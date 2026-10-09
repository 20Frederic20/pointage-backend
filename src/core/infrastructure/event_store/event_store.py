from collections.abc import Mapping, Sequence

from sqlalchemy import delete, insert, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.domain.errors import ConflictError
from core.domain.events import BaseEvent

from .models import EventModel, UniqueKeyModel

EventTypes = Mapping[str, type[BaseEvent]]
"""``event_name`` → event class: how a repository reads its own stream back."""

# Any constant works: every writer takes the same transaction-level lock.
_APPEND_LOCK_KEY = 7_433_001


def to_event(row: EventModel, event_types: EventTypes) -> BaseEvent:
    """Stored row → domain event, with its original id and timestamp."""
    event_type = event_types.get(row.event_name)
    if event_type is None:
        raise TypeError(f"No event type registered for {row.event_name!r} (stream {row.stream_type})")
    event = event_type.from_payload(row.payload)
    event.restore_identity(row.id, row.occurred_at)
    return event


class EventStore:
    """Append-only event streams over the write database session.

    Shares the request session — and so the command's transaction — with
    the transactional outbox and the unique keys: the events, their outbox
    rows and the reserved values commit atomically or not at all.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        """For repositories' own lookups on :class:`EventModel` / its payloads."""
        return self._session

    async def append(
        self,
        *,
        stream_type: str,
        stream_id: str,
        expected_version: int,
        events: Sequence[BaseEvent],
    ) -> None:
        """Append ``events`` after version ``expected_version`` of the stream.

        Raises ``ConflictError`` if another writer appended to the stream
        since it was loaded.
        """
        if not events:
            return
        # ponytail: one global lock per appending transaction, held until
        # commit, so global positions become visible in order and a projection
        # never skips an event committed late. Per-stream ordering (or reading
        # up to the oldest open transaction) if write throughput ever matters.
        await self._session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": _APPEND_LOCK_KEY})
        rows = [
            {
                "id": event.event_id,
                "stream_type": stream_type,
                "stream_id": stream_id,
                "stream_version": expected_version + offset,
                "event_name": event.get_event_name(),
                "payload": event.to_payload(),
                "occurred_at": event.occurred_at,
                "created_at": event.occurred_at,
                "updated_at": event.occurred_at,
                "version_id": 1,
            }
            for offset, event in enumerate(events, start=1)
        ]
        try:
            await self._session.execute(insert(EventModel), rows)
        except IntegrityError as exc:
            raise ConflictError(
                f"{stream_type} {stream_id} was modified concurrently (stale version {expected_version})",
                context=stream_id,
            ) from exc

    async def load(self, stream_id: str, event_types: EventTypes) -> list[BaseEvent]:
        """Every event of one stream, oldest first.

        Empty if the stream does not exist *or is another kind of aggregate*:
        ids share one generator, so a user id must not load as an employee.
        """
        rows = await self._session.scalars(
            select(EventModel)
            .where(EventModel.stream_id == stream_id, EventModel.event_name.in_(list(event_types)))
            .order_by(EventModel.stream_version)
        )
        return [to_event(row, event_types) for row in rows.all()]

    async def load_streams(self, stream_ids: Sequence[str], event_types: EventTypes) -> dict[str, list[BaseEvent]]:
        """Several streams in one query, in the order of ``stream_ids``."""
        if not stream_ids:
            return {}
        rows = await self._session.scalars(
            select(EventModel)
            .where(EventModel.stream_id.in_(stream_ids), EventModel.event_name.in_(list(event_types)))
            .order_by(EventModel.stream_id, EventModel.stream_version)
        )
        streams: dict[str, list[BaseEvent]] = {stream_id: [] for stream_id in stream_ids}
        for row in rows.all():
            streams[row.stream_id].append(to_event(row, event_types))
        return {stream_id: events for stream_id, events in streams.items() if events}

    async def exists(self, stream_id: str, stream_type: str) -> bool:
        """Whether ``stream_id`` is a stream of ``stream_type`` (another kind of aggregate is not)."""
        row = await self._session.scalar(
            select(EventModel.id)
            .where(EventModel.stream_id == stream_id, EventModel.stream_type == stream_type)
            .limit(1)
        )
        return row is not None

    async def any_stream(self, stream_type: str) -> bool:
        """Whether at least one stream of ``stream_type`` exists."""
        row = await self._session.scalar(select(EventModel.id).where(EventModel.stream_type == stream_type).limit(1))
        return row is not None

    async def find_stream_ids(self, stream_type: str, contains: Mapping[str, object] | None = None) -> list[str]:
        """Streams of ``stream_type`` with an event whose payload contains ``contains``.

        Meant for the values an aggregate never changes after creation (the
        employee of a time entry, the directory of a site…): the repository
        then loads the streams and filters on their current state.
        """
        statement = select(EventModel.stream_id).where(EventModel.stream_type == stream_type)
        if contains:
            statement = statement.where(EventModel.payload.contains(dict(contains)))
        statement = statement.group_by(EventModel.stream_id).order_by(text("min(events.global_position)"))
        return list((await self._session.scalars(statement)).all())

    # ---- unique keys ----

    async def owner(self, scope: str, key: str) -> str | None:
        """The stream holding ``key`` in ``scope``, if any."""
        return await self._session.scalar(
            select(UniqueKeyModel.stream_id).where(UniqueKeyModel.scope == scope, UniqueKeyModel.key == key)
        )

    async def reserve(self, scope: str, key: str, stream_id: str) -> None:
        """Take ``key`` for ``stream_id``; ``ConflictError`` if another stream holds it."""
        holder = await self.owner(scope, key)
        if holder == stream_id:
            return
        try:
            await self._session.execute(insert(UniqueKeyModel).values(scope=scope, key=key, stream_id=stream_id))
        except IntegrityError as exc:
            raise ConflictError(f"{scope} {key!r} is already taken", context=key) from exc

    async def release(self, scope: str, key: str, stream_id: str) -> None:
        """Give ``key`` back, if ``stream_id`` holds it."""
        await self._session.execute(
            delete(UniqueKeyModel).where(
                UniqueKeyModel.scope == scope,
                UniqueKeyModel.key == key,
                UniqueKeyModel.stream_id == stream_id,
            )
        )

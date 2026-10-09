import asyncio
import logging
from collections.abc import Callable, Sequence

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio.session import AsyncSession

from core.infrastructure.database.unit_of_work import SQLAlchemyUnitOfWork
from core.infrastructure.event_store import EventModel

from .aggregate_projection import AggregateProjection
from .models import ProjectionCheckpointModel, ProjectionFailureModel

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], AsyncSession]


class ProjectionRunner:
    """Background worker that feeds the read database from the event store.

    One poll = one read-database transaction: the next batch of events (by
    global position, after the checkpoint) is applied to the read models and
    the checkpoint moves forward in the same commit. A crash in the middle
    rolls both back and the next poll redoes the batch — projection is
    exactly-once. The checkpoint row is locked for the poll, so several app
    instances never project the same batch twice.

    An event whose projection fails is rolled back alone (savepoint), logged
    and parked in ``projection_failures``; the runner moves on, so one bad
    event never freezes every read model. Its stream stays stale until the
    cause is fixed and the read models are rebuilt.
    """

    def __init__(
        self,
        *,
        write_session_factory: SessionFactory,
        read_session_factory: SessionFactory,
        projections: Sequence[AggregateProjection],
        name: str = "read_model",
        batch_size: int = 500,
        poll_interval: float = 0.2,
    ) -> None:
        self._write_session_factory = write_session_factory
        self._read_session_factory = read_session_factory
        self._projections = {projection.stream_type: projection for projection in projections}
        self._name = name
        self._batch_size = batch_size
        self._poll_interval = poll_interval
        self._stopping = asyncio.Event()

    async def poll_once(self) -> int:
        """Project one batch; returns how many events were read."""
        async with self._read_session_factory() as read_session:
            async with SQLAlchemyUnitOfWork(read_session):
                checkpoint = await self._lock_checkpoint(read_session)
                async with self._write_session_factory() as write_session:
                    rows = (
                        await write_session.scalars(
                            select(EventModel)
                            .where(EventModel.global_position > checkpoint.position)
                            .order_by(EventModel.global_position)
                            .limit(self._batch_size)
                        )
                    ).all()
                for row in rows:
                    projection = self._projections.get(row.stream_type)
                    if projection is None:
                        continue
                    # Read repositories mix ORM loads and Core updates: start
                    # each event from the database, not from a stale identity map.
                    await read_session.flush()
                    read_session.expunge_all()
                    try:
                        async with read_session.begin_nested():
                            await projection.project(read_session, row)
                    except Exception as error:
                        logger.exception(
                            "projection runner %s: event %s (%s #%s) parked",
                            self._name, row.id, row.stream_type, row.global_position,
                        )
                        await self._park(read_session, row, error)
                if rows:
                    await read_session.execute(
                        update(ProjectionCheckpointModel)
                        .where(ProjectionCheckpointModel.id == self._name)
                        .values(position=rows[-1].global_position)
                    )
                return len(rows)

    async def _park(self, session: AsyncSession, row: EventModel, error: Exception) -> None:
        await session.execute(
            insert(ProjectionFailureModel).values(
                id=row.id,
                runner=self._name,
                global_position=row.global_position,
                stream_type=row.stream_type,
                stream_id=row.stream_id,
                event_name=row.event_name,
                error=f"{type(error).__name__}: {error}"[:4000],
            )
        )

    async def _lock_checkpoint(self, session: AsyncSession) -> ProjectionCheckpointModel:
        """The runner's checkpoint row, locked until the poll commits."""
        statement = (
            select(ProjectionCheckpointModel)
            .where(ProjectionCheckpointModel.id == self._name)
            .with_for_update()
        )
        checkpoint = await session.scalar(statement)
        if checkpoint is None:
            # A racing runner inserting the same row fails this poll only.
            await session.execute(insert(ProjectionCheckpointModel).values(id=self._name, position=0))
            checkpoint = await session.scalar(statement)
        return checkpoint

    async def run(self) -> None:
        """Poll until :meth:`stop` — safe to cancel as a task."""
        while not self._stopping.is_set():
            projected = 0
            try:
                projected = await self.poll_once()
            except Exception:
                logger.exception("projection runner %s: poll failed; retrying next cycle", self._name)
            if projected >= self._batch_size:
                continue  # catching up: no pause between full batches
            try:
                await asyncio.wait_for(self._stopping.wait(), timeout=self._poll_interval)
            except TimeoutError:
                pass

    def stop(self) -> None:
        """Ask :meth:`run` to finish the current poll and exit."""
        self._stopping.set()

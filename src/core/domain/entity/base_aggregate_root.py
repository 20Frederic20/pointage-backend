from collections.abc import Iterable
from datetime import datetime
from typing import Self

from ..events import BaseEvent
from .base_entity import Entity


class AggregateRoot[T](Entity[T]):
    """Base class for aggregate roots.

    An aggregate is a transactional consistency boundary. Domain methods on the
    aggregate mutate state AND record the resulting domain events via
    :meth:`record_event`. The application layer drains the pending events once
    the aggregate is saved (``repo.save(aggregate)``) using :meth:`collect_events`
    and dispatches them through the event bus.

    ``version`` is the persistence stamp of the last durable write — ``0``
    means the aggregate has never been persisted. Repositories use it to
    refuse concurrent writers: an UPDATE matches the aggregate's loaded
    version, so saving an aggregate whose version no longer matches the
    stored row raises ``ConflictError`` instead of silently overwriting
    another writer's changes. After a durable save the repository calls
    :meth:`_advance_version`, so the in-memory aggregate carries the stored
    version and a second save in the same request stays consistent.

    Event sourcing: the aggregate's state is the replay of its events.

    * Domain methods validate, then call :meth:`_raise` with an event that
      carries everything the change needs (including "now" and generated
      ids). ``_raise`` applies the event to the state and records it.
    * Each aggregate implements ``_apply(event)``: a pure state transition,
      with no validation, no clock and no I/O, so replaying the stored
      events always rebuilds the same state.
    * :meth:`rehydrate` rebuilds an aggregate from its stored events; the
      version is the number of events in its stream.
    """

    __slots__ = ("_domain_events", "_version")

    def __init__(
        self,
        entity_id: T,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        *,
        version: int = 0,
    ) -> None:
        super().__init__(entity_id, created_at=created_at, updated_at=updated_at)
        self._domain_events: list[BaseEvent] = []
        self._version = version

    @property
    def version(self) -> int:
        """Persistence stamp of the last durable write (``0`` = never saved)."""
        return self._version

    def _advance_version(self, count: int = 1) -> None:
        """Repository hook: bump the stamp after a successful save.

        A state-table save bumps by one (the stored row's version is always
        ``version + 1``); an event-store save bumps by the number of events
        appended. Only repositories (and their test doubles) call this —
        domain code never versions aggregates itself.
        """
        self._version += count

    # ---- event sourcing ----

    @classmethod
    def rehydrate(cls, aggregate_id: T, events: Iterable[BaseEvent]) -> Self:
        """Rebuild an aggregate by replaying its stored events, oldest first.

        With no events, returns a blank aggregate (version ``0``) whose first
        applied event creates it.
        """
        aggregate = cls.__new__(cls)
        AggregateRoot.__init__(aggregate, aggregate_id)
        for event in events:
            aggregate.apply(event)
            aggregate._version += 1
        return aggregate

    def apply(self, event: BaseEvent) -> None:
        """Apply one event to the state, without recording it.

        Used by replay (:meth:`rehydrate`) and by read-model projections. The
        event's timestamp becomes ``updated_at`` (and ``created_at`` for the
        aggregate's first event); ``_apply`` may override both, e.g. for an
        import event that carries the original dates.
        """
        if self._version == 0 and not self._domain_events:
            self._created_at = event.occurred_at
        self._updated_at = event.occurred_at
        self._apply(event)

    def _raise(self, event: BaseEvent) -> None:
        """Domain-method helper: apply the change, then record it."""
        self.apply(event)
        self.record_event(event)

    def _apply(self, event: BaseEvent) -> None:
        """State transition for one event — implemented by each aggregate."""
        raise NotImplementedError(f"{type(self).__name__} cannot apply {type(event).__name__}")

    @property
    def domain_events(self) -> tuple[BaseEvent, ...]:
        """Read-only view of pending (not-yet-dispatched) domain events."""
        return tuple(self._domain_events)

    def record_event(self, event: BaseEvent) -> None:
        """Record a domain event produced by a state change.

        The event is *not* dispatched here — dispatch happens after the
        aggregate is persisted, via :meth:`collect_events`.
        """
        self._domain_events.append(event)

    def collect_events(self) -> list[BaseEvent]:
        """Drain and return all pending events (atomic read + clear).

        The application layer calls this exactly once, after ``save()``, so
        events are dispatched exactly once and never re-observed.
        """
        events, self._domain_events = self._domain_events, []
        return events

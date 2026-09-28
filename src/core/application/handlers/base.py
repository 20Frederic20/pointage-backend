from abc import abstractmethod
from collections.abc import Sequence

from cqrs.events.event import IEvent
from cqrs.requests.request import ReqT, ResT
from cqrs.requests.request_handler import RequestHandler

from core.application.outbox import IEventOutbox
from core.application.unit_of_work import IUnitOfWork
from core.domain.entity import AggregateRoot
from core.domain.events import BaseEvent


class RequestHandlerBase(RequestHandler[ReqT, ResT]):
    """Shared plumbing for application handlers.

    Records follow-up domain events (``_record``) so the cqrs mediator can
    dispatch them *after* ``handle()`` returns — i.e. after the unit of work
    committed — preserving the "events only once durable" contract.
    """

    def __init__(self) -> None:
        self._events: list[IEvent] = []

    @property
    def events(self) -> Sequence[IEvent]:
        return tuple(self._events)

    def _record(self, event: IEvent) -> None:
        self._events.append(event)


class CommandHandler(RequestHandlerBase[ReqT, ResT]):
    """Base class for write use cases — the command-handler template.

    ``handle`` is a template method: it owns the ordering that makes
    domain-event delivery durable, so subclasses cannot get it wrong
    (forgetting a step, or queueing events outside the transaction):

    1. **Inside one unit of work** — run the domain work (``_execute``),
       persist every changed aggregate (``_persist``), then queue the drained
       events in the transactional outbox. The aggregate write and its event
       rows share one transaction: they commit atomically or vanish together.
    2. **Only after the block exits cleanly** (i.e. after commit) — record
       the same events on the handler for the mediator's post-commit
       dispatch to in-process subscribers.

    Two delivery paths, one durability rule — encoded here once, not
    re-implemented per handler. Subclasses provide only:

    * ``_execute(request)`` — the use case itself: build / load and mutate
      aggregates, no persistence of their own. Returns the result (a DTO or
      ``None``) together with the aggregates the template should persist.
    * ``_persist(aggregate)`` — routes one aggregate to its repository
      (``isinstance`` dispatch when a use case touches several kinds).
    """

    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__()
        self._unit_of_work = unit_of_work
        self._event_outbox = event_outbox

    async def handle(self, request: ReqT) -> ResT:
        """Template method — the ordering *is* the durability guarantee.

        Do not override: subclass behavior goes in ``_execute`` / ``_persist``.
        """
        async with self._unit_of_work:
            result, aggregates = await self._execute(request)
            events: list[BaseEvent] = []
            for aggregate in aggregates:
                await self._persist(aggregate)
                events.extend(aggregate.collect_events())
            for event in events:
                self._queue_in_outbox(event)
        for event in events:
            self._record(event)
        return result

    @abstractmethod
    async def _execute(self, request: ReqT) -> tuple[ResT, Sequence[AggregateRoot]]:
        """Run the use case — called *inside* the unit of work.

        Domain work only: build / load and mutate aggregates. Collecting
        their events, persisting, outbox queueing, and post-commit dispatch
        are the template's job — never do them here.
        """
        ...

    @abstractmethod
    async def _persist(self, aggregate: AggregateRoot) -> None:
        """Save one changed aggregate through its repository."""
        ...

    def _queue_in_outbox(self, event: BaseEvent) -> None:
        """Add the event to the transactional outbox *inside* the transaction."""
        if self._event_outbox is not None:
            self._event_outbox.add(event)


class QueryHandler(RequestHandlerBase[ReqT, ResT]):
    """Base class for read use cases.

    A query handler always returns a result DTO; it never mutates state.
    """

    @abstractmethod
    async def handle(self, request: ReqT) -> ResT:
        ...
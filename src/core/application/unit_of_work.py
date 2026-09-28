from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType


class IUnitOfWork(ABC):
    """Transaction boundary for one request / use case (application-layer port).

    Implemented by infrastructure (``SQLAlchemyUnitOfWork``); the
    ``CommandHandler`` template opens it, persists the changed aggregates and
    queues their outbox events inside it, and dispatches aggregate events
    *after* the block exits cleanly (i.e. after commit), so an event is only
    published once its write is durable. On exception the block rolls back
    and no events are dispatched.
    """

    @abstractmethod
    async def commit(self) -> None:
        """Make the current transaction durable."""
        ...

    @abstractmethod
    async def rollback(self) -> None:
        """Abandon the current transaction."""
        ...

    @abstractmethod
    async def __aenter__(self) -> IUnitOfWork: ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

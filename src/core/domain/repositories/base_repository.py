from abc import ABC, abstractmethod

from ..entity import AggregateRoot


class IRepository[TAggregate: AggregateRoot, TId](ABC):
    """Port for persisting and loading aggregates (domain layer).

    Implemented by infrastructure (SQLAlchemy repositories, mocks, in-memory
    stores). A repository:

    * deals in whole aggregates only — never partial state;
    * persists the aggregate as one transactional unit;
    * does NOT dispatch domain events — the application layer drains them via
      ``aggregate.collect_events()`` after ``save()``;
    * raises ``NotFoundError`` from :meth:`get_by_id` when the aggregate is
      missing, and ``ConflictError`` from :meth:`save` on a concurrent-write
      conflict (optimistic concurrency / uniqueness violation).

    Context repositories extend this base with their own query methods (e.g.
    ``list(filters) -> CursorPage[...]``).
    """

    @abstractmethod
    async def get_by_id(self, aggregate_id: TId) -> TAggregate:
        """Load an aggregate by id.

        Raises ``NotFoundError`` if no aggregate with ``aggregate_id`` exists.
        """
        ...

    @abstractmethod
    async def save(self, aggregate: TAggregate) -> None:
        """Persist an aggregate: insert on the first save, update afterward.

        Raises ``ConflictError`` on a concurrent writing (optimistic
        concurrency / uniqueness violation).
        """
        ...

    @abstractmethod
    async def delete(self, aggregate_id: TId) -> None:
        """Delete an aggregate by id. No-op if it does not exist."""
        ...

    @abstractmethod
    async def exists(self, aggregate_id: TId) -> bool:
        """Whether an aggregate with ``aggregate_id`` exists."""
        ...

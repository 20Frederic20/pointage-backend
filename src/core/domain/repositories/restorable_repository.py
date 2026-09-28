from abc import ABC, abstractmethod

from core.domain.entity import AggregateRoot


class IRestorableRepository[TAggregate: AggregateRoot, TId](ABC):
    """Port for aggregates that support an archive / restore lifecycle.

    Complements: class:`IRepository` for aggregates that are soft-archived
    rather than hard-deleted: normal queries return active rows only, while
    archived aggregates are retrieved explicitly and can be restored.

    Implementations translate ``archive`` / ``restore`` to the underlying
    storage strategy (e.g. setting ``deleted_at`` on a ``SoftDeleteMixin``
    table) and must filter archived rows out of :meth:`find_active_by_id` and
    other queries.

    Concrete repositories extend this base with their own query methods.
    """

    @abstractmethod
    async def find_active_by_id(self, aggregate_id: TId) -> TAggregate:
        """Load a non-archived aggregate by id, or raise ``NotFoundError``."""
        ...

    @abstractmethod
    async def find_archived_by_id(self, aggregate_id: TId) -> TAggregate:
        """Load an archived aggregate by id, or raise ``NotFoundError``."""
        ...

    @abstractmethod
    async def archive(self, aggregate_id: TId) -> TAggregate:
        """Archive the aggregate (soft delete) and return the archived state."""
        ...

    @abstractmethod
    async def restore(self, aggregate_id: TId) -> TAggregate:
        """Restore a previously archived aggregate and return it."""
        ...

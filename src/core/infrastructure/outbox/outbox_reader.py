from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio.session import AsyncSession

from .models import OutboxModel, OutboxStatus

MAX_FLUSHES = 5
"""After this many failed produce attempts a row is parked as FAILED.

FAILED rows stop being retried (they would otherwise poison every batch);
they are visible in the table for an operator to inspect and re-queue."""


class OutboxReader:
    """Read-and-mark side of the outbox, used by the relay's own session.

    Separate from ``TransactionalOutbox`` on purpose: writes happen on the
    request-scoped session inside the handler's transaction, while reads and
    status updates happen later, on the relay worker's session, inside the
    relay's own transaction. Marking a batch is atomic — the unit of work
    around one poll commits status updates for the whole batch at once.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_batch(self, limit: int = 100) -> Sequence[OutboxModel]:
        """Oldest pending rows that have not exhausted their flush budget."""
        statement = (
            select(OutboxModel)
            .where(
                OutboxModel.status == OutboxStatus.PENDING,
                OutboxModel.flush_counter < MAX_FLUSHES,
            )
            .order_by(OutboxModel.created_at, OutboxModel.id)
            .limit(limit)
        )
        return (await self._session.scalars(statement)).all()

    def mark_published(self, row: OutboxModel) -> None:
        row.status = OutboxStatus.PUBLISHED
        row.published_at = datetime.now(UTC)

    def mark_failed(self, row: OutboxModel) -> None:
        """Count one failed produce attempt; park the row once budget is spent."""
        row.flush_counter += 1
        if row.flush_counter >= MAX_FLUSHES:
            row.status = OutboxStatus.FAILED

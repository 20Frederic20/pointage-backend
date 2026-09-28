import asyncio
import logging
from collections.abc import Callable

from cqrs.message_brokers.protocol import Message, MessageBroker
from sqlalchemy.ext.asyncio.session import AsyncSession

from core.infrastructure.database.unit_of_work import SQLAlchemyUnitOfWork

from .outbox_reader import OutboxReader

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], AsyncSession]


class OutboxRelay:
    """Background worker that drains the outbox into the message broker.

    One poll = one transaction: the batch is read, every row is handed to the
    broker, and the status updates commit together with the poll. A successful
    ``send_message`` followed by a crashed relay re-delivers on the next poll
    — delivery is at-least-once, so consumers deduplicate on
    ``payload["event_id"]``.

    Production swaps ``broker`` for a real one (cqrs ships kafka / amqp
    adapters); the relay and everything upstream are unchanged.
    """

    def __init__(
        self,
        *,
        session_factory: SessionFactory,
        broker: MessageBroker,
        batch_size: int = 100,
        poll_interval: float = 1.0,
    ) -> None:
        self._session_factory = session_factory
        self._broker = broker
        self._batch_size = batch_size
        self._poll_interval = poll_interval
        self._stopping = asyncio.Event()

    async def poll_once(self) -> int:
        """Produce one batch; returns how many rows reached the broker."""
        async with self._session_factory() as session:
            reader = OutboxReader(session)
            async with SQLAlchemyUnitOfWork(session):
                rows = await reader.get_batch(self._batch_size)
                for row in rows:
                    try:
                        await self._broker.send_message(
                            Message(
                                message_name=row.event_name,
                                topic=row.topic,
                                payload=row.payload,
                            )
                        )
                    except Exception:
                        logger.exception(
                            "outbox: producing %s (%s) failed",
                            row.event_name,
                            row.event_id,
                        )
                        reader.mark_failed(row)
                    else:
                        reader.mark_published(row)
                return len(rows)

    async def run(self) -> None:
        """Poll forever until :meth:`stop` — safe to cancel as a task."""
        while not self._stopping.is_set():
            try:
                await self.poll_once()
            except Exception:
                # Storage hiccup (DB down, commit failed) — statuses revert to
                # their pre-poll values and the next poll retries.
                logger.exception("outbox relay: poll failed; retrying next cycle")
            try:
                await asyncio.wait_for(
                    self._stopping.wait(), timeout=self._poll_interval
                )
            except TimeoutError:
                pass

    def stop(self) -> None:
        """Ask :meth:`run` to finish the current poll and exit."""
        self._stopping.set()

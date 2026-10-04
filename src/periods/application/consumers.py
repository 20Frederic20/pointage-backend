"""Logging consumers for the periods integration events.

No downstream subscribers yet: these no-ops mark the outbox rows published.
Replace them when real subscribers arrive; the notifications themselves are
the contract.
"""

import logging

from cqrs.events import EventHandler

from .notifications import PeriodClosedNotification, PeriodLockedNotification, PeriodOpenedNotification

logger = logging.getLogger(__name__)


def _log(notification) -> None:
    logger.info(
        "periods event %s (%s) aggregate=%s",
        notification.event_name,
        notification.event_id,
        notification.payload.get("period_id"),
    )


class PeriodOpenedConsumer(EventHandler[PeriodOpenedNotification]):
    async def handle(self, event: PeriodOpenedNotification) -> None:
        _log(event)


class PeriodLockedConsumer(EventHandler[PeriodLockedNotification]):
    async def handle(self, event: PeriodLockedNotification) -> None:
        _log(event)


class PeriodClosedConsumer(EventHandler[PeriodClosedNotification]):
    async def handle(self, event: PeriodClosedNotification) -> None:
        _log(event)


PERIODS_CONSUMERS: dict[type, type] = {
    PeriodOpenedNotification: PeriodOpenedConsumer,
    PeriodLockedNotification: PeriodLockedConsumer,
    PeriodClosedNotification: PeriodClosedConsumer,
}

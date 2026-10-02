import logging

from cqrs.events import EventHandler

from .notifications import TimeEntryCreatedNotification

logger = logging.getLogger(__name__)


def _log(notification) -> None:
    logger.info(
        "punchs event %s (%s) aggregate=%s",
        notification.event_name,
        notification.event_id,
        notification.payload.get("time_entry_id")
        or notification.payload.get("user_id"),
    )


class TimeEntryCreatedConsumer(
    EventHandler[TimeEntryCreatedNotification]
):
    async def handle(self, event: TimeEntryCreatedNotification) -> None:
        _log(event)


PUNCHES_CONSUMERS: dict[type, type] = {
    TimeEntryCreatedNotification: TimeEntryCreatedConsumer,
}

"""Logging consumers for the absences integration events.

No downstream subscribers yet (time calculation will be the first): these
no-ops mark the outbox rows published. Replace them when real subscribers
arrive; the notifications themselves are the contract.
"""

import logging

from cqrs.events import EventHandler

from .notifications import (
    AbsenceApprovedNotification,
    AbsenceDeclaredNotification,
    AbsenceRejectedNotification,
)

logger = logging.getLogger(__name__)


def _log(notification) -> None:
    logger.info(
        "absences event %s (%s) aggregate=%s",
        notification.event_name,
        notification.event_id,
        notification.payload.get("absence_id"),
    )


class AbsenceDeclaredConsumer(EventHandler[AbsenceDeclaredNotification]):
    async def handle(self, event: AbsenceDeclaredNotification) -> None:
        _log(event)


class AbsenceApprovedConsumer(EventHandler[AbsenceApprovedNotification]):
    async def handle(self, event: AbsenceApprovedNotification) -> None:
        _log(event)


class AbsenceRejectedConsumer(EventHandler[AbsenceRejectedNotification]):
    async def handle(self, event: AbsenceRejectedNotification) -> None:
        _log(event)


ABSENCES_CONSUMERS: dict[type, type] = {
    AbsenceDeclaredNotification: AbsenceDeclaredConsumer,
    AbsenceApprovedNotification: AbsenceApprovedConsumer,
    AbsenceRejectedNotification: AbsenceRejectedConsumer,
}

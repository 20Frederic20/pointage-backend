"""Logging consumers for the adjustments integration events.

No downstream subscribers yet: these no-ops prove the pipeline and mark the
outbox rows published. Replace them when real subscribers arrive.
"""

import logging

from cqrs.events import EventHandler

from .notifications import (
    AnomalyCreatedNotification,
    RegularizationRequestCreatedNotification,
)

logger = logging.getLogger(__name__)


def _log(notification) -> None:
    logger.info(
        "adjustments event %s (%s) aggregate=%s",
        notification.event_name,
        notification.event_id,
        notification.payload.get("anomaly_id")
        or notification.payload.get("regularization_request_id"),
    )


class AnomalyCreatedConsumer(EventHandler[AnomalyCreatedNotification]):
    async def handle(self, event: AnomalyCreatedNotification) -> None:
        _log(event)


class RegularizationRequestCreatedConsumer(
    EventHandler[RegularizationRequestCreatedNotification]
):
    async def handle(
        self, event: RegularizationRequestCreatedNotification
    ) -> None:
        _log(event)


ADJUSTMENTS_CONSUMERS: dict[type, type] = {
    AnomalyCreatedNotification: AnomalyCreatedConsumer,
    RegularizationRequestCreatedNotification: RegularizationRequestCreatedConsumer,
}

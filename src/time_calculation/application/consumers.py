"""Logging consumers for the time calculation integration events.

No downstream subscribers yet: these no-ops mark the outbox rows published.
Replace them when real subscribers arrive; the notifications themselves are
the contract.
"""

import logging

from cqrs.events import EventHandler

from .notifications import (
    CalculationRuleVersionCreatedNotification,
    DailyTimeResultCalculatedNotification,
    DailyTimeResultValidatedNotification,
)

logger = logging.getLogger(__name__)


def _log(notification) -> None:
    logger.info(
        "time calculation event %s (%s) aggregate=%s",
        notification.event_name,
        notification.event_id,
        notification.payload.get("daily_time_result_id")
        or notification.payload.get("calculation_rule_version_id"),
    )


class CalculationRuleVersionCreatedConsumer(EventHandler[CalculationRuleVersionCreatedNotification]):
    async def handle(self, event: CalculationRuleVersionCreatedNotification) -> None:
        _log(event)


class DailyTimeResultCalculatedConsumer(EventHandler[DailyTimeResultCalculatedNotification]):
    async def handle(self, event: DailyTimeResultCalculatedNotification) -> None:
        _log(event)


class DailyTimeResultValidatedConsumer(EventHandler[DailyTimeResultValidatedNotification]):
    async def handle(self, event: DailyTimeResultValidatedNotification) -> None:
        _log(event)


TIME_CALCULATION_CONSUMERS: dict[type, type] = {
    CalculationRuleVersionCreatedNotification: CalculationRuleVersionCreatedConsumer,
    DailyTimeResultCalculatedNotification: DailyTimeResultCalculatedConsumer,
    DailyTimeResultValidatedNotification: DailyTimeResultValidatedConsumer,
}

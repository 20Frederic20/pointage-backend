"""Logging consumers for the planning integration events.

No downstream subscribers yet: these no-ops mark the outbox rows published.
Replace them when real subscribers arrive; the notifications themselves are
the contract.
"""

import logging

from cqrs.events import EventHandler

from .notifications import (
    EmployeeScheduleAssignedNotification,
    EmployeeScheduleEndedNotification,
    TimeProfileCreatedNotification,
    TimeProfileVersionAddedNotification,
)

logger = logging.getLogger(__name__)


def _log(notification) -> None:
    logger.info(
        "planning event %s (%s) aggregate=%s",
        notification.event_name,
        notification.event_id,
        notification.payload.get("time_profile_id")
        or notification.payload.get("employee_schedule_id"),
    )


class TimeProfileCreatedConsumer(EventHandler[TimeProfileCreatedNotification]):
    async def handle(self, event: TimeProfileCreatedNotification) -> None:
        _log(event)


class TimeProfileVersionAddedConsumer(EventHandler[TimeProfileVersionAddedNotification]):
    async def handle(self, event: TimeProfileVersionAddedNotification) -> None:
        _log(event)


class EmployeeScheduleAssignedConsumer(EventHandler[EmployeeScheduleAssignedNotification]):
    async def handle(self, event: EmployeeScheduleAssignedNotification) -> None:
        _log(event)


class EmployeeScheduleEndedConsumer(EventHandler[EmployeeScheduleEndedNotification]):
    async def handle(self, event: EmployeeScheduleEndedNotification) -> None:
        _log(event)


PLANNING_CONSUMERS: dict[type, type] = {
    TimeProfileCreatedNotification: TimeProfileCreatedConsumer,
    TimeProfileVersionAddedNotification: TimeProfileVersionAddedConsumer,
    EmployeeScheduleAssignedNotification: EmployeeScheduleAssignedConsumer,
    EmployeeScheduleEndedNotification: EmployeeScheduleEndedConsumer,
}

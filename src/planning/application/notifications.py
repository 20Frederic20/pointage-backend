"""Integration events of the planning context — the outbox wire format.

The outbox relay rehydrates by ``event_name`` from the registry, so these
names are part of the contract — do not rename them casually.
"""

import uuid
from dataclasses import dataclass

from cqrs.events.event import DCNotificationEvent

from core.domain.events import BaseEvent

from ..domain.events import (
    EmployeeScheduleAssigned,
    EmployeeScheduleEnded,
    TimeProfileCreated,
    TimeProfileVersionAdded,
)

PLANNING_TOPIC = "planning"


@dataclass(frozen=True)
class TimeProfileCreatedNotification(DCNotificationEvent[dict]):
    pass


@dataclass(frozen=True)
class TimeProfileVersionAddedNotification(DCNotificationEvent[dict]):
    pass


@dataclass(frozen=True)
class EmployeeScheduleAssignedNotification(DCNotificationEvent[dict]):
    pass


@dataclass(frozen=True)
class EmployeeScheduleEndedNotification(DCNotificationEvent[dict]):
    pass


def _notification(
    notification_type: type[DCNotificationEvent[dict]],
    event: BaseEvent,
    payload: dict,
) -> DCNotificationEvent[dict]:
    """Shared plumbing: base metadata plus the event's specifics."""
    return notification_type(
        event_name=event.get_event_name(),
        payload=payload,
        event_id=uuid.uuid4(),
        event_timestamp=event.occurred_at,
        topic=PLANNING_TOPIC,
    )


def to_time_profile_created(event: TimeProfileCreated) -> TimeProfileCreatedNotification:
    return _notification(
        TimeProfileCreatedNotification,
        event,
        {"time_profile_id": event.get_aggregate_id().value},
    )


def to_time_profile_version_added(
    event: TimeProfileVersionAdded,
) -> TimeProfileVersionAddedNotification:
    return _notification(
        TimeProfileVersionAddedNotification,
        event,
        {
            "time_profile_id": event.get_aggregate_id().value,
            "time_profile_version_id": event.time_profile_version_id.value,
        },
    )


def to_employee_schedule_assigned(
    event: EmployeeScheduleAssigned,
) -> EmployeeScheduleAssignedNotification:
    return _notification(
        EmployeeScheduleAssignedNotification,
        event,
        {"employee_schedule_id": event.get_aggregate_id().value},
    )


def to_employee_schedule_ended(event: EmployeeScheduleEnded) -> EmployeeScheduleEndedNotification:
    return _notification(
        EmployeeScheduleEndedNotification,
        event,
        {"employee_schedule_id": event.get_aggregate_id().value},
    )


PLANNING_EVENT_MAPPERS: dict[type, object] = {
    TimeProfileCreated: to_time_profile_created,
    TimeProfileVersionAdded: to_time_profile_version_added,
    EmployeeScheduleAssigned: to_employee_schedule_assigned,
    EmployeeScheduleEnded: to_employee_schedule_ended,
}

PLANNING_EVENT_REGISTRY: dict[str, type] = {
    "planning.time_profile.created": TimeProfileCreatedNotification,
    "planning.time_profile.version_added": TimeProfileVersionAddedNotification,
    "planning.employee_schedule.assigned": EmployeeScheduleAssignedNotification,
    "planning.employee_schedule.ended": EmployeeScheduleEndedNotification,
}

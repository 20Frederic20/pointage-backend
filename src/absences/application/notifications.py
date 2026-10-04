"""Integration events of the absences context — the outbox wire format.

The outbox relay rehydrates by ``event_name`` from the registry, so these
names are part of the contract — do not rename them casually.
"""

import uuid
from dataclasses import dataclass

from cqrs.events.event import DCNotificationEvent

from core.domain.events import BaseEvent

from ..domain.events import AbsenceApproved, AbsenceDeclared, AbsenceRejected

ABSENCES_TOPIC = "absences"


@dataclass(frozen=True)
class AbsenceDeclaredNotification(DCNotificationEvent[dict]):
    pass


@dataclass(frozen=True)
class AbsenceApprovedNotification(DCNotificationEvent[dict]):
    pass


@dataclass(frozen=True)
class AbsenceRejectedNotification(DCNotificationEvent[dict]):
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
        topic=ABSENCES_TOPIC,
    )


def to_absence_declared(event: AbsenceDeclared) -> AbsenceDeclaredNotification:
    return _notification(
        AbsenceDeclaredNotification,
        event,
        {"absence_id": event.get_aggregate_id().value},
    )


def to_absence_approved(event: AbsenceApproved) -> AbsenceApprovedNotification:
    return _notification(
        AbsenceApprovedNotification,
        event,
        {"absence_id": event.get_aggregate_id().value},
    )


def to_absence_rejected(event: AbsenceRejected) -> AbsenceRejectedNotification:
    return _notification(
        AbsenceRejectedNotification,
        event,
        {"absence_id": event.get_aggregate_id().value},
    )


ABSENCES_EVENT_MAPPERS: dict[type, object] = {
    AbsenceDeclared: to_absence_declared,
    AbsenceApproved: to_absence_approved,
    AbsenceRejected: to_absence_rejected,
}

ABSENCES_EVENT_REGISTRY: dict[str, type] = {
    "absences.absence.declared": AbsenceDeclaredNotification,
    "absences.absence.approved": AbsenceApprovedNotification,
    "absences.absence.rejected": AbsenceRejectedNotification,
}

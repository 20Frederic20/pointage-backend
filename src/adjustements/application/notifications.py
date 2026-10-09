"""Integration events of the adjustments context — the outbox wire format.

Event names are part of the contract: the relay rehydrates by name from
``ADJUSTMENTS_EVENT_REGISTRY``, so keep them in sync with the domain events.
"""

import uuid
from dataclasses import dataclass

from cqrs.events.event import DCNotificationEvent

from core.domain.events import BaseEvent

from ..domain.events import (
    AnomalyCreated,
    AnomalyImported,
    AnomalyResolved,
    RegularizationRequestCreated,
    RegularizationRequestImported,
)

ADJUSTMENTS_TOPIC = "adjustments"


@dataclass(frozen=True)
class AnomalyCreatedNotification(DCNotificationEvent[dict]):
    pass


@dataclass(frozen=True)
class AnomalyResolvedNotification(DCNotificationEvent[dict]):
    pass


@dataclass(frozen=True)
class RegularizationRequestCreatedNotification(DCNotificationEvent[dict]):
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
        topic=ADJUSTMENTS_TOPIC,
    )


def to_anomaly_created(event: AnomalyCreated) -> AnomalyCreatedNotification:
    return _notification(
        AnomalyCreatedNotification,
        event,
        {"anomaly_id": event.get_aggregate_id().value},
    )


def to_anomaly_resolved(event: AnomalyResolved) -> AnomalyResolvedNotification:
    return _notification(
        AnomalyResolvedNotification,
        event,
        {"anomaly_id": event.get_aggregate_id().value},
    )


def to_regularization_request_created(
    event: RegularizationRequestCreated,
) -> RegularizationRequestCreatedNotification:
    return _notification(
        RegularizationRequestCreatedNotification,
        event,
        {"regularization_request_id": event.get_aggregate_id().value},
    )


ADJUSTMENTS_EVENT_MAPPERS: dict[type, object] = {
    AnomalyCreated: to_anomaly_created,
    AnomalyResolved: to_anomaly_resolved,
    RegularizationRequestCreated: to_regularization_request_created,
    # Takeover of the state tables: stored, never published.
    AnomalyImported: None,
    RegularizationRequestImported: None,
}

ADJUSTMENTS_EVENT_REGISTRY: dict[str, type] = {
    "adjustments.anomaly.created": AnomalyCreatedNotification,
    "adjustments.anomaly.resolved": AnomalyResolvedNotification,
    "adjustments.regularization_request.created": (
        RegularizationRequestCreatedNotification
    ),
}

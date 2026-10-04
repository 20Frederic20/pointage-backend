"""Integration events of the periods context — the outbox wire format.

The outbox relay rehydrates by ``event_name`` from the registry, so these
names are part of the contract — do not rename them casually.
"""

import uuid
from dataclasses import dataclass

from cqrs.events.event import DCNotificationEvent

from core.domain.events import BaseEvent

from ..domain.events import PeriodClosed, PeriodLocked, PeriodOpened

PERIODS_TOPIC = "periods"


@dataclass(frozen=True)
class PeriodOpenedNotification(DCNotificationEvent[dict]):
    pass


@dataclass(frozen=True)
class PeriodLockedNotification(DCNotificationEvent[dict]):
    pass


@dataclass(frozen=True)
class PeriodClosedNotification(DCNotificationEvent[dict]):
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
        topic=PERIODS_TOPIC,
    )


def to_period_opened(event: PeriodOpened) -> PeriodOpenedNotification:
    return _notification(PeriodOpenedNotification, event, {"period_id": event.get_aggregate_id().value})


def to_period_locked(event: PeriodLocked) -> PeriodLockedNotification:
    return _notification(PeriodLockedNotification, event, {"period_id": event.get_aggregate_id().value})


def to_period_closed(event: PeriodClosed) -> PeriodClosedNotification:
    return _notification(PeriodClosedNotification, event, {"period_id": event.get_aggregate_id().value})


PERIODS_EVENT_MAPPERS: dict[type, object] = {
    PeriodOpened: to_period_opened,
    PeriodLocked: to_period_locked,
    PeriodClosed: to_period_closed,
}

PERIODS_EVENT_REGISTRY: dict[str, type] = {
    "periods.period.opened": PeriodOpenedNotification,
    "periods.period.locked": PeriodLockedNotification,
    "periods.period.closed": PeriodClosedNotification,
}

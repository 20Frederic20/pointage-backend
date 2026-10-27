import uuid
from dataclasses import dataclass
from typing import Any

from cqrs.events.event import DCNotificationEvent

from core.domain.events import BaseEvent
from punch.domain.events import TimeEntryCreated, TimeEntryImported, TimeEntryRejected, TimeEntryValidated

PUNCHES_TOPIC = "punches"


@dataclass(frozen=True)
class TimeEntryCreatedNotification(DCNotificationEvent[dict]):
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
        topic=PUNCHES_TOPIC,
    )

def _to_time_entry_created(
    event: TimeEntryCreated
) -> DCNotificationEvent[dict[Any, Any]]:
    return _notification(
        TimeEntryCreatedNotification,
        event,
        {"time_entry_id": event.get_aggregate_id().value},
    )

PUNCHES_EVENT_MAPPERS: dict[type, object] = {
    TimeEntryCreated: _to_time_entry_created,
    # Takeover of the state tables: stored, never published.
    TimeEntryImported: None,
    # Decisions only change the read model for now.
    TimeEntryValidated: None,
    TimeEntryRejected: None,
}

PUNCHES_EVENT_REGISTRY  = {
    "punchs.time_entry.created": TimeEntryCreatedNotification,
}
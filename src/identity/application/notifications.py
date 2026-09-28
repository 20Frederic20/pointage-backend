"""Integration events of the users context — the outbox wire format.

One concrete :class:`DCNotificationEvent` subclass per domain event (a bare
``DCNotificationEvent[dict]`` alias would rehydrate as the base class and
miss the cqrs EventMap's type-based dispatch), plus one mapper per event.
The outbox relay rehydrates by ``event_name`` from the registry, so these
names are part of the contract — do not rename them casually.
"""

import uuid
from dataclasses import dataclass

from cqrs.events.event import DCNotificationEvent

from core.domain.events import BaseEvent

from ..domain.events import (
    DirectoryCreated,
    UserDeactivated,
    UserRegistered,
    UserRoleChanged,
)

USERS_TOPIC = "users"


@dataclass(frozen=True)
class DirectoryCreatedNotification(DCNotificationEvent[dict]):
    pass


@dataclass(frozen=True)
class UserRegisteredNotification(DCNotificationEvent[dict]):
    pass


@dataclass(frozen=True)
class UserRoleChangedNotification(DCNotificationEvent[dict]):
    pass


@dataclass(frozen=True)
class UserDeactivatedNotification(DCNotificationEvent[dict]):
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
        topic=USERS_TOPIC,
    )


def to_workspace_created(
    event: DirectoryCreated
) -> DirectoryCreatedNotification:
    return _notification(
        DirectoryCreatedNotification,
        event,
        {"directory_id": event.get_aggregate_id().value},
    )


def to_user_registered(event: UserRegistered) -> UserRegisteredNotification:
    return _notification(
        UserRegisteredNotification,
        event,
        {
            "user_id": event.get_aggregate_id().value,
            "directory_id": event.directory_id.value,
        },
    )


def to_user_role_changed(
    event: UserRoleChanged
) -> UserRoleChangedNotification:
    return _notification(
        UserRoleChangedNotification,
        event,
        {
            "user_id": event.get_aggregate_id().value,
            "old_role": event.old_role.value,
            "new_role": event.new_role.value,
        },
    )


def to_user_deactivated(event: UserDeactivated) -> UserDeactivatedNotification:
    return _notification(
        UserDeactivatedNotification,
        event,
        {"user_id": event.get_aggregate_id().value},
    )


USERS_EVENT_MAPPERS: dict[type, object] = {
    DirectoryCreated: to_workspace_created,
    UserRegistered: to_user_registered,
    UserRoleChanged: to_user_role_changed,
    UserDeactivated: to_user_deactivated,
}

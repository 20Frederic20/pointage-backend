"""Logging consumers for the users integration events.

Phase 1 has no downstream subscribers yet (no email, no analytics), so the
outbox relay binds these no-ops — they prove the full pipeline (aggregate →
outbox → relay → consumer) and mark the notification rows published rather
than leaving them parked. Replace individual consumers when real
subscribers arrive; the notifications themselves are the contract.
"""

import logging

from cqrs.events import EventHandler

from .notifications import (
    DirectoryCreatedNotification,
    EmployeeAssignedNotification,
    EmployeeAssignmentEndedNotification,
    EmployeeCreatedNotification,
    SiteActivatedNotification,
    SiteCreatedNotification,
    SiteDeactivatedNotification,
    SiteMadePrincipalNotification,
    UserDeactivatedNotification,
    UserRegisteredNotification,
    UserRoleChangedNotification,
)

logger = logging.getLogger(__name__)


def _log(notification) -> None:
    logger.info(
        "users event %s (%s) aggregate=%s",
        notification.event_name,
        notification.event_id,
        notification.payload.get("directory_id")
        or notification.payload.get("user_id")
        or notification.payload.get("employee_id")
        or notification.payload.get("site_id")
        or notification.payload.get("employee_assignment_id"),
    )


class DirectoryCreatedConsumer(
    EventHandler[DirectoryCreatedNotification]
):
    async def handle(self, event: DirectoryCreatedNotification) -> None:
        _log(event)


class EmployeeCreatedConsumer(
    EventHandler[EmployeeCreatedNotification]
):
    async def handle(self, event: EmployeeCreatedNotification)  -> None:
        _log(event)


class UserRegisteredConsumer(EventHandler[UserRegisteredNotification]):
    async def handle(self, event: UserRegisteredNotification) -> None:
        _log(event)


class UserRoleChangedConsumer(EventHandler[UserRoleChangedNotification]):
    async def handle(self, event: UserRoleChangedNotification) -> None:
        _log(event)


class UserDeactivatedConsumer(EventHandler[UserDeactivatedNotification]):
    async def handle(self, event: UserDeactivatedNotification) -> None:
        _log(event)


class SiteCreatedConsumer(EventHandler[SiteCreatedNotification]):
    async def handle(self, event: SiteCreatedNotification) -> None:
        _log(event)


class SiteActivatedConsumer(EventHandler[SiteActivatedNotification]):
    async def handle(self, event: SiteActivatedNotification) -> None:
        _log(event)


class SiteDeactivatedConsumer(EventHandler[SiteDeactivatedNotification]):
    async def handle(self, event: SiteDeactivatedNotification) -> None:
        _log(event)


class SiteMadePrincipalConsumer(EventHandler[SiteMadePrincipalNotification]):
    async def handle(self, event: SiteMadePrincipalNotification) -> None:
        _log(event)


class EmployeeAssignedConsumer(EventHandler[EmployeeAssignedNotification]):
    async def handle(self, event: EmployeeAssignedNotification) -> None:
        _log(event)


class EmployeeAssignmentEndedConsumer(EventHandler[EmployeeAssignmentEndedNotification]):
    async def handle(self, event: EmployeeAssignmentEndedNotification) -> None:
        _log(event)


USERS_CONSUMERS: dict[type, type] = {
    DirectoryCreatedNotification: DirectoryCreatedConsumer,
    EmployeeCreatedNotification: EmployeeCreatedConsumer,
    UserRegisteredNotification: UserRegisteredConsumer,
    UserRoleChangedNotification: UserRoleChangedConsumer,
    UserDeactivatedNotification: UserDeactivatedConsumer,
    SiteCreatedNotification: SiteCreatedConsumer,
    SiteActivatedNotification: SiteActivatedConsumer,
    SiteDeactivatedNotification: SiteDeactivatedConsumer,
    SiteMadePrincipalNotification: SiteMadePrincipalConsumer,
    EmployeeAssignedNotification: EmployeeAssignedConsumer,
    EmployeeAssignmentEndedNotification: EmployeeAssignmentEndedConsumer,
}
"""Event-store adapter for the User aggregate (write side)."""

from core.domain.errors import NotFoundError
from core.domain.specifications import Specification
from core.infrastructure.event_store import EventStore

from ...domain.entities import User
from ...domain.events import (
    UserActivityRecorded,
    UserDeactivated,
    UserImported,
    UserPasswordCleared,
    UserProfileUpdated,
    UserRegistered,
    UserRoleChanged,
)
from ...domain.repositories import IUserRepository
from ...domain.value_objects.ids import UserId

USER_STREAM = "identity.user"

USER_EVENT_TYPES = {
    "users.user.registered": UserRegistered,
    "users.user.role_changed": UserRoleChanged,
    "users.user.deactivated": UserDeactivated,
    "users.user.profile_updated": UserProfileUpdated,
    "users.user.password_cleared": UserPasswordCleared,
    "users.user.activity_recorded": UserActivityRecorded,
    "users.user.imported": UserImported,
}

EMAIL_KEY = "identity.user.email"


class EventSourcedUserRepository(IUserRepository):
    """A user is the replay of its stream; the email is a unique key."""

    def __init__(self, event_store: EventStore) -> None:
        self._store = event_store

    async def get_by_id(self, user_id: UserId) -> User:
        events = await self._store.load(user_id.value, USER_EVENT_TYPES)
        if not events:
            raise NotFoundError(f"User {user_id} not found", context=user_id.value)
        return User.rehydrate(user_id, events)

    async def exists(self, user_id: UserId) -> bool:
        return await self._store.exists(user_id.value, USER_STREAM)

    async def find_by_email(self, email: str) -> User | None:
        owner = await self._store.owner(EMAIL_KEY, email.strip().lower())
        return await self.get_by_id(UserId(owner)) if owner is not None else None

    async def exists_any(self) -> bool:
        return await self._store.any_stream(USER_STREAM)

    async def find(self, spec: Specification[User], *, limit: int = 50, offset: int = 0) -> list[User]:
        raise NotImplementedError("Listing users is a query: read the users read model")

    async def count(self, spec: Specification[User]) -> int:
        raise NotImplementedError("Counting users is a query: read the users read model")

    async def count_active(self) -> int:
        raise NotImplementedError("Counting users is a query: read the users read model")

    async def save(self, user: User) -> None:
        events = user.domain_events
        for event in events:
            # The email never changes after registration.
            if isinstance(event, UserRegistered | UserImported):
                await self._store.reserve(EMAIL_KEY, event.email, user.id.value)
        await self._store.append(
            stream_type=USER_STREAM, stream_id=user.id.value, expected_version=user.version, events=events
        )
        user._advance_version(len(events))

    async def delete(self, user_id: UserId) -> None:
        raise NotImplementedError("Event-sourced users are never deleted")

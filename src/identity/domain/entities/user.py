"""The User aggregate — a workspace member and their role."""

from datetime import UTC, datetime
from typing import Self

from core.domain.entity import AggregateRoot

from ..events.user_events import (
    UserActivityRecorded,
    UserDeactivated,
    UserImported,
    UserPasswordCleared,
    UserProfileUpdated,
    UserRegistered,
    UserRoleChanged,
)
from ..value_objects.ids import UserId
from ..value_objects.role import Role


def _utcnow() -> datetime:
    return datetime.now(UTC)


class User(AggregateRoot[UserId]):
    """A member of one workspace (PRD §6.1).

    Owns the credentials the auth context verifies (the password hash is a
    plain field — hashing itself is an application-layer concern through
    the ``PasswordHasher`` port) and the role that drives RBAC.
    """

    __slots__ = (
        "_avatar_url",
        "_email",
        "_first_name",
        "_is_active",
        "_last_active_at",
        "_last_name",
        "_password_hash",
        "_role",
    )

    def __init__(
        self,
        user_id: UserId,
        *,
        email: str,
        password_hash: str | None,
        role: Role = Role.EMPLOYEE,
        first_name: str | None = None,
        last_name: str | None = None,
        avatar_url: str | None = None,
        is_active: bool = True,
        last_active_at: datetime | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        version: int = 0,
    ) -> None:
        super().__init__(
            user_id, created_at=created_at, updated_at=updated_at,
            version=version
        )
        self._email = email.strip().lower()
        self._password_hash = password_hash
        self._role = role
        self._first_name = first_name
        self._last_name = last_name
        self._avatar_url = avatar_url
        self._is_active = is_active
        self._last_active_at = last_active_at

    # ---- construction ----

    @classmethod
    def register_owner(
        cls,
        user_id: UserId,
        *,
        email: str,
        password_hash: str | None,
        role: Role = Role.EMPLOYEE,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> Self:
        """
        Founding signup: the first user of a brand-new workspace, an ADMIN.
        """
        user = cls.rehydrate(user_id, [])
        user._raise(
            UserRegistered(
                user_id,
                email=email.strip().lower(),
                password_hash=password_hash,
                role=role,
                first_name=first_name,
                last_name=last_name,
            )
        )
        return user

    # ---- state changes ----

    def change_role(self, new_role: Role) -> Role:
        """
        Set a new role; returns the previous one.
        A no-op keeps the event log clean.
        """
        old_role = self._role
        if new_role is not old_role:
            self._raise(UserRoleChanged(self.id, old_role=old_role, new_role=new_role))
        return old_role

    def deactivate(self) -> None:
        """
        Deactivate the member. Idempotent — an inactive user records nothing.
        """
        if not self._is_active:
            return
        self._raise(UserDeactivated(self.id))

    def update_profile(
        self,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        avatar_url: str | None = None,
    ) -> None:
        """
        Apply only the fields the caller actually sent (``None`` = untouched).
        Nothing changed: nothing recorded.
        """
        event = UserProfileUpdated(
            self.id,
            first_name=first_name if first_name is not None else self._first_name,
            last_name=last_name if last_name is not None else self._last_name,
            avatar_url=avatar_url if avatar_url is not None else self._avatar_url,
        )
        if (event.first_name, event.last_name, event.avatar_url) == (self._first_name, self._last_name, self._avatar_url):
            return
        self._raise(event)

    def clear_password(self) -> None:
        """
        Remove the password: the account then logs in with an emailed code.
        Idempotent.
        """
        if self._password_hash is None:
            return
        self._raise(UserPasswordCleared(self.id))

    def record_activity(self) -> None:
        """
        Best-effort presence telemetry (auth calls it on each login/refresh).
        """
        self._raise(UserActivityRecorded(self.id, last_active_at=_utcnow()))

    # ---- event sourcing ----

    def _apply(self, event) -> None:
        match event:
            case UserRegistered():
                self._email = event.email
                self._password_hash = event.password_hash
                self._role = event.role
                self._first_name = event.first_name
                self._last_name = event.last_name
                self._avatar_url = None
                self._is_active = True
                self._last_active_at = None
            case UserRoleChanged():
                self._role = event.new_role
            case UserDeactivated():
                self._is_active = False
            case UserProfileUpdated():
                self._first_name = event.first_name
                self._last_name = event.last_name
                self._avatar_url = event.avatar_url
            case UserPasswordCleared():
                self._password_hash = None
            case UserActivityRecorded():
                self._last_active_at = event.last_active_at
            case UserImported():
                self._email = event.email
                self._password_hash = event.password_hash
                self._role = event.role
                self._first_name = event.first_name
                self._last_name = event.last_name
                self._avatar_url = event.avatar_url
                self._is_active = event.is_active
                self._last_active_at = event.last_active_at
                self._created_at = event.created_at
            case _:
                super()._apply(event)

    # ---- read side ----

    @property
    def email(self) -> str:
        return self._email

    @property
    def password_hash(self) -> str | None:
        """``None``: no password, the account logs in with an emailed code."""
        return self._password_hash

    @property
    def role(self) -> Role:
        return self._role

    @property
    def first_name(self) -> str | None:
        return self._first_name

    @property
    def last_name(self) -> str | None:
        return self._last_name

    @property
    def avatar_url(self) -> str | None:
        return self._avatar_url

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def last_active_at(self) -> datetime | None:
        return self._last_active_at

"""Domain events of the users bounded context."""

from datetime import datetime

from core.domain.events import BaseEvent, decode_datetime, encode_datetime

from ..value_objects.ids import DirectoryId, UserId
from ..value_objects.role import Role


class DirectoryCreated(BaseEvent[DirectoryId]):
    """A new directory (tenant) was created."""

    def __init__(
        self,
        directory_id: DirectoryId,
        *,
        code: str,
        name: str,
        parent_directory_id: DirectoryId | None,
    ) -> None:
        super().__init__()
        self.directory_id = directory_id
        self.code = code
        self.name = name
        self.parent_directory_id = parent_directory_id

    def get_aggregate_id(self) -> DirectoryId:
        return self.directory_id

    def get_event_name(self) -> str:
        return "users.directory.created"

    def to_payload(self) -> dict:
        return {
            "directory_id": self.directory_id.value,
            "code": self.code,
            "name": self.name,
            "parent_directory_id": self.parent_directory_id.value if self.parent_directory_id else None,
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "DirectoryCreated":
        parent = payload["parent_directory_id"]
        return cls(
            DirectoryId(payload["directory_id"]),
            code=payload["code"],
            name=payload["name"],
            parent_directory_id=DirectoryId(parent) if parent else None,
        )


class DirectoryUpdated(BaseEvent[DirectoryId]):
    """A directory's code and/or name changed (the event holds the new values)."""

    def __init__(self, directory_id: DirectoryId, *, code: str, name: str) -> None:
        super().__init__()
        self.directory_id = directory_id
        self.code = code
        self.name = name

    def get_aggregate_id(self) -> DirectoryId:
        return self.directory_id

    def get_event_name(self) -> str:
        return "users.directory.updated"

    def to_payload(self) -> dict:
        return {"directory_id": self.directory_id.value, "code": self.code, "name": self.name}

    @classmethod
    def from_payload(cls, payload: dict) -> "DirectoryUpdated":
        return cls(DirectoryId(payload["directory_id"]), code=payload["code"], name=payload["name"])


class DirectoryImported(BaseEvent[DirectoryId]):
    """A directory taken over from the state tables when event sourcing started."""

    def __init__(
        self,
        directory_id: DirectoryId,
        *,
        code: str,
        name: str,
        parent_directory_id: DirectoryId | None,
        created_at: datetime,
    ) -> None:
        super().__init__()
        self.directory_id = directory_id
        self.code = code
        self.name = name
        self.parent_directory_id = parent_directory_id
        self.created_at = created_at

    def get_aggregate_id(self) -> DirectoryId:
        return self.directory_id

    def get_event_name(self) -> str:
        return "users.directory.imported"

    def to_payload(self) -> dict:
        return {
            "directory_id": self.directory_id.value,
            "code": self.code,
            "name": self.name,
            "parent_directory_id": self.parent_directory_id.value if self.parent_directory_id else None,
            "created_at": encode_datetime(self.created_at),
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "DirectoryImported":
        parent = payload["parent_directory_id"]
        return cls(
            DirectoryId(payload["directory_id"]),
            code=payload["code"],
            name=payload["name"],
            parent_directory_id=DirectoryId(parent) if parent else None,
            created_at=decode_datetime(payload["created_at"]),
        )


class UserRegistered(BaseEvent[UserId]):
    """A user joined a directory — as the founding owner or via an invite."""

    def __init__(
        self,
        user_id: UserId,
        *,
        email: str,
        password_hash: str | None,
        role: Role,
        first_name: str | None,
        last_name: str | None,
    ) -> None:
        super().__init__()
        self.user_id = user_id
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.first_name = first_name
        self.last_name = last_name

    def get_aggregate_id(self) -> UserId:
        return self.user_id

    def get_event_name(self) -> str:
        return "users.user.registered"

    def to_payload(self) -> dict:
        return {
            "user_id": self.user_id.value,
            "email": self.email,
            "password_hash": self.password_hash,
            "role": self.role.value,
            "first_name": self.first_name,
            "last_name": self.last_name,
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "UserRegistered":
        return cls(
            UserId(payload["user_id"]),
            email=payload["email"],
            password_hash=payload["password_hash"],
            role=Role(payload["role"]),
            first_name=payload["first_name"],
            last_name=payload["last_name"],
        )


class UserRoleChanged(BaseEvent[UserId]):
    """A user's role changed inside their directory."""

    def __init__(
        self, user_id: UserId, *, old_role: Role, new_role: Role
    ) -> None:
        super().__init__()
        self.user_id = user_id
        self.old_role = old_role
        self.new_role = new_role

    def get_aggregate_id(self) -> UserId:
        return self.user_id

    def get_event_name(self) -> str:
        return "users.user.role_changed"

    def to_payload(self) -> dict:
        return {"user_id": self.user_id.value, "old_role": self.old_role.value, "new_role": self.new_role.value}

    @classmethod
    def from_payload(cls, payload: dict) -> "UserRoleChanged":
        return cls(UserId(payload["user_id"]), old_role=Role(payload["old_role"]), new_role=Role(payload["new_role"]))


class UserDeactivated(BaseEvent[UserId]):
    """A user was deactivated and can no longer authenticate."""

    def __init__(self, user_id: UserId) -> None:
        super().__init__()
        self.user_id = user_id

    def get_aggregate_id(self) -> UserId:
        return self.user_id

    def get_event_name(self) -> str:
        return "users.user.deactivated"

    def to_payload(self) -> dict:
        return {"user_id": self.user_id.value}

    @classmethod
    def from_payload(cls, payload: dict) -> "UserDeactivated":
        return cls(UserId(payload["user_id"]))


class UserProfileUpdated(BaseEvent[UserId]):
    """A user's profile changed (the event holds the resulting values)."""

    def __init__(
        self,
        user_id: UserId,
        *,
        first_name: str | None,
        last_name: str | None,
        avatar_url: str | None,
    ) -> None:
        super().__init__()
        self.user_id = user_id
        self.first_name = first_name
        self.last_name = last_name
        self.avatar_url = avatar_url

    def get_aggregate_id(self) -> UserId:
        return self.user_id

    def get_event_name(self) -> str:
        return "users.user.profile_updated"

    def to_payload(self) -> dict:
        return {
            "user_id": self.user_id.value,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "avatar_url": self.avatar_url,
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "UserProfileUpdated":
        return cls(
            UserId(payload["user_id"]),
            first_name=payload["first_name"],
            last_name=payload["last_name"],
            avatar_url=payload["avatar_url"],
        )


class UserPasswordCleared(BaseEvent[UserId]):
    """A user's password was removed: the account now logs in with an emailed code."""

    def __init__(self, user_id: UserId) -> None:
        super().__init__()
        self.user_id = user_id

    def get_aggregate_id(self) -> UserId:
        return self.user_id

    def get_event_name(self) -> str:
        return "users.user.password_cleared"

    def to_payload(self) -> dict:
        return {"user_id": self.user_id.value}

    @classmethod
    def from_payload(cls, payload: dict) -> "UserPasswordCleared":
        return cls(UserId(payload["user_id"]))


class UserActivityRecorded(BaseEvent[UserId]):
    """A user logged in or refreshed their session."""

    def __init__(self, user_id: UserId, *, last_active_at: datetime) -> None:
        super().__init__()
        self.user_id = user_id
        self.last_active_at = last_active_at

    def get_aggregate_id(self) -> UserId:
        return self.user_id

    def get_event_name(self) -> str:
        return "users.user.activity_recorded"

    def to_payload(self) -> dict:
        return {"user_id": self.user_id.value, "last_active_at": encode_datetime(self.last_active_at)}

    @classmethod
    def from_payload(cls, payload: dict) -> "UserActivityRecorded":
        return cls(UserId(payload["user_id"]), last_active_at=decode_datetime(payload["last_active_at"]))


class UserImported(BaseEvent[UserId]):
    """A user taken over from the state tables when event sourcing started."""

    def __init__(
        self,
        user_id: UserId,
        *,
        email: str,
        password_hash: str | None,
        role: Role,
        first_name: str | None,
        last_name: str | None,
        avatar_url: str | None,
        is_active: bool,
        last_active_at: datetime | None,
        created_at: datetime,
    ) -> None:
        super().__init__()
        self.user_id = user_id
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.first_name = first_name
        self.last_name = last_name
        self.avatar_url = avatar_url
        self.is_active = is_active
        self.last_active_at = last_active_at
        self.created_at = created_at

    def get_aggregate_id(self) -> UserId:
        return self.user_id

    def get_event_name(self) -> str:
        return "users.user.imported"

    def to_payload(self) -> dict:
        return {
            "user_id": self.user_id.value,
            "email": self.email,
            "password_hash": self.password_hash,
            "role": self.role.value,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "avatar_url": self.avatar_url,
            "is_active": self.is_active,
            "last_active_at": encode_datetime(self.last_active_at),
            "created_at": encode_datetime(self.created_at),
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "UserImported":
        return cls(
            UserId(payload["user_id"]),
            email=payload["email"],
            password_hash=payload["password_hash"],
            role=Role(payload["role"]),
            first_name=payload["first_name"],
            last_name=payload["last_name"],
            avatar_url=payload["avatar_url"],
            is_active=payload["is_active"],
            last_active_at=decode_datetime(payload["last_active_at"]),
            created_at=decode_datetime(payload["created_at"]),
        )

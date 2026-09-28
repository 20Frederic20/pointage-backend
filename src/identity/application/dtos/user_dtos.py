"""Frozen DTOs returned by the users handlers.

Ids are plain strings on DTOs — the branded id value objects stay in the
domain. ``UserCredentialsDTO`` carries the password hash and is consumed
only by the auth context's login handler; it never crosses the HTTP
boundary. ``InviteDTO.token`` is populated exactly once, on creation — the
raw token is never persisted.
"""

from dataclasses import dataclass
from datetime import datetime

from core.application import DTO
from identity.domain.value_objects.location import Location

from ...domain.entities import Directory, User
from ...domain.value_objects import Role


@dataclass(frozen=True)
class UserDTO(DTO):
    id: str
    directory_id: str
    email: str
    role: Role
    is_active: bool
    first_name: str | None = None
    last_name: str | None = None
    avatar_url: str | None = None
    last_active_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_aggregate(cls, user: User) -> "UserDTO":
        return cls(
            id=user.id.value,
            directory_id=user.directory_id.value,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            first_name=user.first_name,
            last_name=user.last_name,
            avatar_url=user.avatar_url,
            last_active_at=user.last_active_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


@dataclass(frozen=True)
class UserCredentialsDTO(DTO):
    """Login inputs resolved from an email — including the password hash.

    Application-layer only: the auth context verifies it and must never
    serialize it to the wire.
    """

    id: str
    directory_id: str
    email: str
    password_hash: str
    role: Role
    is_active: bool

    @classmethod
    def from_aggregate(cls, user: User) -> "UserCredentialsDTO":
        return cls(
            id=user.id.value,
            directory_id=user.directory_id.value,
            email=user.email,
            password_hash=user.password_hash,
            role=user.role,
            is_active=user.is_active,
        )


@dataclass(frozen=True)
class DirectoryDTO(DTO):
    id: str
    name: str
    code: str
    location: Location
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_aggregate(cls, workspace: Directory) -> "DirectoryDTO":
        return cls(
            id=workspace.id.value,
            name=workspace.name,
            code=workspace.code,
            location=workspace.location,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )


@dataclass(frozen=True)
class UsersPageDTO(DTO):
    items: tuple[UserDTO, ...]
    total: int

"""Wire schemas of the users context (camelCase JSON contract).

Pydantic lives only here at the interface — domain objects and DTOs are
plain dataclasses and never leak to the wire. Requests accept both
snake_case and camelCase (``populate_by_name``); responses always dump
``by_alias=True``.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class _CamelSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


# ---- requests --------------------------------------------------------------


class RegisterRequest(_CamelSchema):
    email: EmailStr
    password: str = Field(min_length=8)
    first_name: str | None = None
    last_name: str | None = None
    workspace_name: str | None = Field(default=None, alias="workspaceName")


class AcceptInviteRequest(_CamelSchema):
    password: str = Field(min_length=8)
    first_name: str | None = None
    last_name: str | None = None


class CreateInviteRequest(_CamelSchema):
    email: EmailStr
    role: str


class ChangeRoleRequest(_CamelSchema):
    role: str


class UpdateProfileRequest(_CamelSchema):
    first_name: str | None = None
    last_name: str | None = None
    avatar_url: str | None = Field(default=None, alias="avatarUrl")


class UpdateWorkspaceRequest(_CamelSchema):
    name: str = Field(min_length=1)


# ---- responses -------------------------------------------------------------


class RoleSchema(StrEnum):
    """The wire form of a role (mirrors the domain enum's values)."""

    AGENT = "AGENT"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"


class UserResponse(_CamelSchema):
    id: str
    directory_id: str = Field(alias="DirectoryId")
    email: EmailStr
    role: RoleSchema
    is_active: bool = Field(alias="isActive")
    first_name: str | None = Field(default=None, alias="firstName")
    last_name: str | None = Field(default=None, alias="lastName")
    avatar_url: str | None = Field(default=None, alias="avatarUrl")
    last_active_at: datetime | None = Field(default=None, alias="lastActiveAt")
    created_at: datetime | None = Field(default=None, alias="createdAt")
    updated_at: datetime | None = Field(default=None, alias="updatedAt")


class UserListResponse(_CamelSchema):
    items: list[UserResponse]
    total: int


class InviteResponse(_CamelSchema):
    id: str
    directory_id: str = Field(alias="DirectoryId")
    email: EmailStr
    role: RoleSchema
    status: str
    expires_at: datetime = Field(alias="expiresAt")
    created_by: str = Field(alias="createdBy")
    token: str | None = None  # present only in the creation response


class WorkspaceResponse(_CamelSchema):
    id: str
    name: str
    plan: str
    seat_limit: int = Field(alias="seatLimit")
    created_at: datetime | None = Field(default=None, alias="createdAt")
    updated_at: datetime | None = Field(default=None, alias="updatedAt")
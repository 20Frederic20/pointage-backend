"""Wire schemas of the users context (camelCase JSON contract).

Pydantic lives only here at the interface — domain objects and DTOs are
plain dataclasses and never leak to the wire. Requests accept both
snake_case and camelCase (``populate_by_name``); responses always dump
``by_alias=True``.
"""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from identity.domain import Role
from identity.domain.value_objects.location import Location


class _CamelSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


# ---- requests --------------------------------------------------------------


class RegisterRequest(_CamelSchema):
    email: EmailStr
    # Omitted: the account logs in with a code sent by email.
    password: str | None = Field(default=None, min_length=8)
    first_name: str | None = None
    last_name: str | None = None
    directory_name: str | None = Field(default=None, alias="directoryName")
    # Ignored for the founding account (always ADMIN); EMPLOYEE when omitted.
    role: Role | None = None


class CreateEmployeeRequest(_CamelSchema):

    user_id: str
    directory_id: str
    role: Role = Field(default=Role.EMPLOYEE)
    employee_number: str = Field(min_length=10)
    is_active: bool = Field(default=False)
    phone: str | None = Field(default=None, min_length=10)
    # First day of the initial assignment to ``directory_id``; today when omitted.
    assignment_start_date: date | None = None
    # Site of the initial assignment; the directory's principal site when omitted.
    site_id: str | None = None


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


class UpdateEmployeeRequest(_CamelSchema):

    employee_number: str | None = Field(default=None, min_length=10)
    phone: str | None = Field(default=None, min_length=10)


class CreateDirectoryRequest(_CamelSchema):
    code: str
    name: str
    parent_directory_id: str | None = None


class CreateSiteRequest(_CamelSchema):
    directory_id: str
    name: str = Field(min_length=1, max_length=255)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    address: str | None = Field(default=None, max_length=512)


class AssignEmployeeRequest(_CamelSchema):
    employee_id: str
    directory_id: str
    # Precise punching site; the directory's principal site when omitted.
    site_id: str | None = None
    start_date: date
    end_date: date | None = None


class EndEmployeeAssignmentRequest(_CamelSchema):
    end_date: date


class UpdateDirectoryRequest(_CamelSchema):
    name: str = Field(min_length=1)


# ---- responses -------------------------------------------------------------


class RoleSchema(StrEnum):
    """The wire form of a role (mirrors the domain enum's values)."""
    EMPLOYEE = "EMPLOYEE"
    MANAGER = "MANAGER"
    HR = "HR"
    PAYROLL = "PAYROLL"
    ADMIN = "ADMIN"


class UserResponse(_CamelSchema):
    id: str
    email: EmailStr
    role: RoleSchema
    is_active: bool = Field(alias="isActive")
    first_name: str | None = Field(default=None, alias="firstName")
    last_name: str | None = Field(default=None, alias="lastName")
    avatar_url: str | None = Field(default=None, alias="avatarUrl")
    last_active_at: datetime | None = Field(default=None, alias="lastActiveAt")
    created_at: datetime | None = Field(default=None, alias="createdAt")
    updated_at: datetime | None = Field(default=None, alias="updatedAt")


class EmployeeResponse(_CamelSchema):

    id: str
    role: RoleSchema
    employee_number: str = Field(alias="employeeNumber")
    is_active: bool = Field(alias="isActive")
    phone: str | None = Field(default=None)
    user_id: str = Field(alias="userId")
    created_at: datetime | None = Field(default=None, alias="createdAt")
    updated_at: datetime | None = Field(default=None, alias="updatedAt")


class EmployeeListResponse(_CamelSchema):
    items: list[EmployeeResponse]
    total: int


class UserListResponse(_CamelSchema):
    items: list[UserResponse]
    total: int


class DirectoryResponse(_CamelSchema):
    id: str
    name: str
    code: str
    parent_directory_id: str | None = Field(default=None, alias="parentDirectoryId")
    created_at: datetime | None = Field(default=None, alias="createdAt")
    updated_at: datetime | None = Field(default=None, alias="updatedAt")


class SiteResponse(_CamelSchema):
    id: str
    directory_id: str = Field(alias="directoryId")
    name: str
    location: Location
    kind: str
    active: bool
    address: str | None = None
    created_at: datetime | None = Field(default=None, alias="createdAt")
    updated_at: datetime | None = Field(default=None, alias="updatedAt")


class EmployeeAssignmentResponse(_CamelSchema):
    id: str
    employee_id: str = Field(alias="employeeId")
    directory_id: str = Field(alias="directoryId")
    site_id: str = Field(alias="siteId")
    start_date: date = Field(alias="startDate")
    end_date: date | None = Field(default=None, alias="endDate")
    created_at: datetime | None = Field(default=None, alias="createdAt")
    updated_at: datetime | None = Field(default=None, alias="updatedAt")

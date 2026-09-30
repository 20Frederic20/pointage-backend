"""Interface layer of the users bounded context — routers and wire schemas."""

from .dependencies import get_users
from .schemas import (
    ChangeRoleRequest,
    CreateEmployeeRequest,
    DirectoryResponse,
    EmployeeListResponse,
    EmployeeResponse,
    RegisterRequest,
    UpdateDirectoryRequest,
    UpdateEmployeeRequest,
    UpdateProfileRequest,
    UserListResponse,
    UserResponse,
)

__all__ = [
    "ChangeRoleRequest",
    "CreateEmployeeRequest",
    "DirectoryResponse",
    "EmployeeListResponse",
    "EmployeeResponse",
    "RegisterRequest",
    "UpdateDirectoryRequest",
    "UpdateEmployeeRequest",
    "UpdateProfileRequest",
    "UserListResponse",
    "UserResponse",
    "get_users",
]
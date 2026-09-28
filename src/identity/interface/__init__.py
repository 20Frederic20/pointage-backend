"""Interface layer of the users bounded context — routers and wire schemas."""

from .dependencies import get_users
from .schemas import (
    AcceptInviteRequest,
    ChangeRoleRequest,
    CreateInviteRequest,
    InviteResponse,
    RegisterRequest,
    UpdateProfileRequest,
    UpdateWorkspaceRequest,
    UserListResponse,
    UserResponse,
    WorkspaceResponse,
)

__all__ = [
    "AcceptInviteRequest",
    "ChangeRoleRequest",
    "CreateInviteRequest",
    "InviteResponse",
    "RegisterRequest",
    "UpdateProfileRequest",
    "UpdateWorkspaceRequest",
    "UserListResponse",
    "UserResponse",
    "WorkspaceResponse",
    "get_users",
]
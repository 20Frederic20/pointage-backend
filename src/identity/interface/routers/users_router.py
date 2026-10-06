"""User-facing routes: account creation.

The other authenticated routes (listing, profiles, role changes,
deactivation) join this router with the auth context's guards in a later
slice.
"""

from fastapi import APIRouter, Depends, status

from auth.application.dtos import PrincipalDTO
from auth.interface import get_current_principal, get_optional_principal

from ...application import (
    ClearUserPasswordCommand,
    RegisterUserCommand,
)
from ...infrastructure import UsersContainer
from ..dependencies import get_users
from ..schemas import (
    RegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/users", tags=["users"])


def _user_response(dto) -> UserResponse:
    """DTO (dataclass) → wire schema, camelCase by alias."""
    return UserResponse.model_validate(dto, from_attributes=True)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: RegisterRequest,
    users: UsersContainer = Depends(get_users),  # noqa: B008
    principal: PrincipalDTO | None = Depends(get_optional_principal),  # noqa: B008
) -> UserResponse:
    """Create an account.

    Public while no account exists (the founding ADMIN); afterwards it needs
    an ADMIN access token, otherwise ``403 REGISTRATION_CLOSED``.
    """
    dto = await users.send(
        RegisterUserCommand(
            email=payload.email,
            password=payload.password,
            first_name=payload.first_name,
            last_name=payload.last_name,
            directory_name=payload.directory_name,
            role=payload.role,
            requested_by_role=principal.role if principal else None,
        )
    )
    return _user_response(dto)


@router.post("/{user_id}/password/clear", response_model=UserResponse)
async def clear_password(
    user_id: str,
    users: UsersContainer = Depends(get_users),  # noqa: B008
    principal: PrincipalDTO = Depends(get_current_principal),  # noqa: B008
) -> UserResponse:
    """Remove a member's password (ADMIN only): they log in with an emailed
    code from now on. Also the way out of a forgotten password."""
    dto = await users.send(
        ClearUserPasswordCommand(user_id=user_id, actor_id=principal.user_id)
    )
    return _user_response(dto)

"""User-facing routes: bootstrap signup and invite redemption (public).

The authenticated routes (listing, profiles, role changes, deactivation)
join this router with the auth context's guards in a later slice — see the
route table in ``social_crm_ddd_architecture.md``.
"""

from fastapi import APIRouter, Depends, status

from ...application import (
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
) -> UserResponse:
    """Bootstrap signup: create the first workspace and its ADMIN.

    Closes with ``403 REGISTRATION_CLOSED`` once any workspace exists.
    """
    dto = await users.send(
        RegisterUserCommand(
            email=payload.email,
            password=payload.password,
            first_name=payload.first_name,
            last_name=payload.last_name,
            directory_name=payload.directory_name,
        )
    )
    return _user_response(dto)

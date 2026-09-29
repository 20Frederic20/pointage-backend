"""Workspace routes. ``GET/PATCH /directories/me`` joins this router together
with the auth context's guards in a later slice."""

from fastapi import APIRouter, Depends, status

from identity.application.commands.create_directory import CreateDirectoryCommand
from identity.domain.value_objects.location import Location
from identity.infrastructure import UsersContainer
from identity.interface.schemas import CreateDirectoryRequest, DirectoryResponse

from ..dependencies import get_users

router = APIRouter(prefix="/directories", tags=["directories"])


def _directory_reponse(dto) -> DirectoryResponse:
    """DTO (dataclass) → wire schema, camelCase by alias."""
    return DirectoryResponse.model_validate(dto, from_attributes=True)


@router.post(
    "",
    response_model=DirectoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create(
    payload: CreateDirectoryRequest,
    users: UsersContainer = Depends(get_users),
) -> DirectoryResponse:
    dto = await users.send(
        CreateDirectoryCommand(
            name=payload.name,
            code=payload.code,
            location=Location(payload.latitude, payload.longitude)
        )
    )

    return _directory_reponse(dto)

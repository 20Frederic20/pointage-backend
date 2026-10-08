"""Workspace routes. ``GET/PATCH /directories/me`` joins this routers together
with the auth context's guards in a later slice."""

from fastapi import APIRouter, Depends, status

from identity.application.commands.create_directory import CreateDirectoryCommand
from identity.application.queries import GetDirectorySitesQuery
from identity.infrastructure import UsersContainer
from identity.interface.schemas import CreateDirectoryRequest, DirectoryResponse, SiteResponse

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
    users: UsersContainer = Depends(get_users),  # noqa: B008
) -> DirectoryResponse:
    dto = await users.send(
        CreateDirectoryCommand(
            name=payload.name,
            code=payload.code,
            parent_directory_id=payload.parent_directory_id,
        )
    )

    return _directory_reponse(dto)


@router.get("/{directory_id}/sites", response_model=list[SiteResponse])
async def list_sites(
    directory_id: str,
    users: UsersContainer = Depends(get_users),  # noqa: B008
) -> list[SiteResponse]:
    """Principal site first, then the annexes by name."""
    dtos = await users.send(GetDirectorySitesQuery(directory_id=directory_id))
    return [SiteResponse.model_validate(dto, from_attributes=True) for dto in dtos]

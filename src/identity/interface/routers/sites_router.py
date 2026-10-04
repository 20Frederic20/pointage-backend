"""Site routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from identity.application.commands import ActivateSiteCommand, CreateSiteCommand, DeactivateSiteCommand
from identity.application.queries import GetSiteByIdQuery
from identity.infrastructure import UsersContainer
from identity.interface.schemas import CreateSiteRequest, SiteResponse

from ..dependencies import get_users

router = APIRouter(prefix="/sites", tags=["sites"])


def _site_response(dto) -> SiteResponse:
    """DTO (dataclass) → wire schema, camelCase by alias."""
    return SiteResponse.model_validate(dto, from_attributes=True)


@router.post(
    "",
    response_model=SiteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create(
    payload: CreateSiteRequest,
    users: UsersContainer = Depends(get_users),  # noqa: B008
) -> SiteResponse:
    dto = await users.send(CreateSiteCommand(name=payload.name, address=payload.address))
    return _site_response(dto)


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(
    site_id: str,
    users: UsersContainer = Depends(get_users),  # noqa: B008
) -> SiteResponse:
    dto = await users.send(GetSiteByIdQuery(site_id=site_id))
    if dto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return _site_response(dto)


@router.post("/{site_id}/activate", response_model=SiteResponse)
async def activate(
    site_id: str,
    users: UsersContainer = Depends(get_users),  # noqa: B008
) -> SiteResponse:
    dto = await users.send(ActivateSiteCommand(site_id=site_id))
    return _site_response(dto)


@router.post("/{site_id}/deactivate", response_model=SiteResponse)
async def deactivate(
    site_id: str,
    users: UsersContainer = Depends(get_users),  # noqa: B008
) -> SiteResponse:
    dto = await users.send(DeactivateSiteCommand(site_id=site_id))
    return _site_response(dto)

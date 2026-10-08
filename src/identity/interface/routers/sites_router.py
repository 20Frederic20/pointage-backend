"""Site routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from identity.application.commands import (
    ActivateSiteCommand,
    CreateSiteCommand,
    DeactivateSiteCommand,
    MakeSitePrincipalCommand,
)
from identity.application.queries import GetSiteByIdQuery
from identity.domain.value_objects.location import Location
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
    dto = await users.send(
        CreateSiteCommand(
            directory_id=payload.directory_id,
            name=payload.name,
            location=Location(payload.latitude, payload.longitude),
            address=payload.address,
        )
    )
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


@router.post("/{site_id}/make-principal", response_model=SiteResponse)
async def make_principal(
    site_id: str,
    users: UsersContainer = Depends(get_users),  # noqa: B008
) -> SiteResponse:
    """The directory's current principal site becomes an annex."""
    dto = await users.send(MakeSitePrincipalCommand(site_id=site_id))
    return _site_response(dto)

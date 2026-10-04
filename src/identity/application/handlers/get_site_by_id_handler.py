"""Load one site."""

from core.application import QueryHandler
from core.domain.errors import NotFoundError

from ...domain.repositories import ISiteRepository
from ...domain.value_objects.ids import SiteId
from ..dtos import SiteDTO
from ..queries import GetSiteByIdQuery


class GetSiteByIdHandler(QueryHandler[GetSiteByIdQuery, SiteDTO | None]):
    def __init__(self, *, site_repository: ISiteRepository) -> None:
        super().__init__()
        self._sites = site_repository

    async def handle(self, request: GetSiteByIdQuery) -> SiteDTO | None:
        try:
            site = await self._sites.get_by_id(SiteId(request.site_id))
        except NotFoundError:
            return None
        return SiteDTO.from_aggregate(site)

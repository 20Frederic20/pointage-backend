"""List the sites of a directory, principal first."""

from core.application import QueryHandler

from ...domain.repositories import IDirectoryRepository, ISiteRepository
from ...domain.value_objects.ids import DirectoryId
from ..dtos import SiteDTO
from ..queries import GetDirectorySitesQuery


class GetDirectorySitesHandler(QueryHandler[GetDirectorySitesQuery, list[SiteDTO]]):
    def __init__(
        self,
        *,
        site_repository: ISiteRepository,
        directory_repository: IDirectoryRepository,
    ) -> None:
        super().__init__()
        self._sites = site_repository
        self._directories = directory_repository

    async def handle(self, request: GetDirectorySitesQuery) -> list[SiteDTO]:
        directory = await self._directories.get_by_id(DirectoryId(request.directory_id))
        return [SiteDTO.from_aggregate(site) for site in await self._sites.find_by_directory(directory.id)]

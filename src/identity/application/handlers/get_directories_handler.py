"""Paged directory listing, by name."""

from core.application import QueryHandler

from ...domain.repositories import IDirectoryRepository
from ..dtos import DirectoriesPageDTO, DirectoryDTO
from ..queries import GetDirectoriesQuery


class GetDirectoriesHandler(QueryHandler[GetDirectoriesQuery, DirectoriesPageDTO]):
    def __init__(self, *, directory_repository: IDirectoryRepository) -> None:
        super().__init__()
        self._directories = directory_repository

    async def handle(self, request: GetDirectoriesQuery) -> DirectoriesPageDTO:
        directories = await self._directories.find(limit=request.limit, offset=request.offset)
        total = await self._directories.count()
        return DirectoriesPageDTO(
            items=tuple(DirectoryDTO.from_aggregate(d) for d in directories),
            total=total,
        )

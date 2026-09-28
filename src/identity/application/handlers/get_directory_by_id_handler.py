"""Load one directory by id."""

from core.application import QueryHandler
from core.domain.errors import NotFoundError

from ...domain.repositories import IDirectoryRepository
from ...domain.value_objects.ids import DirectoryId
from ..dtos import DirectoryDTO
from ..queries import GetDirectoryByIdQuery


class GetDirectoryByIdHandler(
    QueryHandler[GetDirectoryByIdQuery, DirectoryDTO | None]
):
    def __init__(self, *, directory_repository: IDirectoryRepository) -> None:
        super().__init__()
        self._directorys = directory_repository

    async def handle(
        self, request: GetDirectoryByIdQuery
    ) -> DirectoryDTO | None:
        try:
            directory = await self._directorys.get_by_id(
                DirectoryId(request.directory_id)
            )
        except NotFoundError:
            return None
        return DirectoryDTO.from_aggregate(directory)

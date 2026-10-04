"""Load one time profile with its versions."""

from core.application import QueryHandler
from core.domain.errors import NotFoundError

from ...domain.repositories import ITimeProfileRepository
from ...domain.value_objects import TimeProfileId
from ..dtos import TimeProfileDTO
from ..queries import GetTimeProfileByIdQuery


class GetTimeProfileByIdHandler(QueryHandler[GetTimeProfileByIdQuery, TimeProfileDTO | None]):
    def __init__(self, *, time_profile_repository: ITimeProfileRepository) -> None:
        super().__init__()
        self._time_profiles = time_profile_repository

    async def handle(self, request: GetTimeProfileByIdQuery) -> TimeProfileDTO | None:
        try:
            time_profile = await self._time_profiles.get_by_id(TimeProfileId(request.time_profile_id))
        except NotFoundError:
            return None
        return TimeProfileDTO.from_aggregate(time_profile)

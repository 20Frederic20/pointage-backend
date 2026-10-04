"""Load one daily time result."""

from core.application import QueryHandler
from core.domain.errors import NotFoundError

from ...domain.repositories import IDailyTimeResultRepository
from ...domain.value_objects import DailyTimeResultId
from ..dtos import DailyTimeResultDTO
from ..queries import GetDailyTimeResultByIdQuery


class GetDailyTimeResultByIdHandler(QueryHandler[GetDailyTimeResultByIdQuery, DailyTimeResultDTO | None]):
    def __init__(self, *, daily_time_result_repository: IDailyTimeResultRepository) -> None:
        super().__init__()
        self._results = daily_time_result_repository

    async def handle(self, request: GetDailyTimeResultByIdQuery) -> DailyTimeResultDTO | None:
        try:
            result = await self._results.get_by_id(DailyTimeResultId(request.daily_time_result_id))
        except NotFoundError:
            return None
        return DailyTimeResultDTO.from_aggregate(result)

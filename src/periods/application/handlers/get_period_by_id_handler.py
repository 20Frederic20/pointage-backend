"""Load one period."""

from core.application import QueryHandler
from core.domain.errors import NotFoundError

from ...domain.repositories import IPeriodRepository
from ...domain.value_objects import PeriodId
from ..dtos import PeriodDTO
from ..queries import GetPeriodByIdQuery


class GetPeriodByIdHandler(QueryHandler[GetPeriodByIdQuery, PeriodDTO | None]):
    def __init__(self, *, period_repository: IPeriodRepository) -> None:
        super().__init__()
        self._periods = period_repository

    async def handle(self, request: GetPeriodByIdQuery) -> PeriodDTO | None:
        try:
            period = await self._periods.get_by_id(PeriodId(request.period_id))
        except NotFoundError:
            return None
        return PeriodDTO.from_aggregate(period)

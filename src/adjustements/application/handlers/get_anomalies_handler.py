"""Back-office anomaly list (read database)."""

from core.application import QueryHandler

from ..dtos import AnomalyListPageDTO
from ..ports import IAnomalyReadRepository
from ..queries import GetAnomaliesQuery


class GetAnomaliesHandler(QueryHandler[GetAnomaliesQuery, AnomalyListPageDTO]):
    def __init__(self, *, anomaly_read_repository: IAnomalyReadRepository) -> None:
        super().__init__()
        self._anomalies = anomaly_read_repository

    async def handle(self, request: GetAnomaliesQuery) -> AnomalyListPageDTO:
        items = await self._anomalies.find(
            status=request.status, type=request.type, limit=request.limit, offset=request.offset
        )
        total = await self._anomalies.count(status=request.status, type=request.type)
        return AnomalyListPageDTO(items=tuple(items), total=total)

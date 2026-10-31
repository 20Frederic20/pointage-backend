"""One back-office anomaly row (read database)."""

from core.application import QueryHandler

from ..dtos import AnomalyListItemDTO
from ..ports import IAnomalyReadRepository
from ..queries import GetAnomalyByIdQuery


class GetAnomalyByIdHandler(QueryHandler[GetAnomalyByIdQuery, AnomalyListItemDTO | None]):
    def __init__(self, *, anomaly_read_repository: IAnomalyReadRepository) -> None:
        super().__init__()
        self._anomalies = anomaly_read_repository

    async def handle(self, request: GetAnomalyByIdQuery) -> AnomalyListItemDTO | None:
        return await self._anomalies.get(request.anomaly_id)

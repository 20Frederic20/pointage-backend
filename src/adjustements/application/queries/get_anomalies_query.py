from dataclasses import dataclass

from core.application import Query

from ...domain.value_objects import AnomalyStatus, AnomalyType
from ..dtos import AnomalyListPageDTO


@dataclass(frozen=True)
class GetAnomaliesQuery(Query):
    """Back-office list, newest detection first."""

    status: AnomalyStatus | None = None
    type: AnomalyType | None = None
    limit: int = 20
    offset: int = 0

    Result = AnomalyListPageDTO

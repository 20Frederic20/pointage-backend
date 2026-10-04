from dataclasses import dataclass

from core.application import Query
from ..dtos import AnomalyDTO


@dataclass(frozen=True)
class GetAnomalyByIdQuery(Query):
    anomaly_id: str

    Result: AnomalyDTO | None = None


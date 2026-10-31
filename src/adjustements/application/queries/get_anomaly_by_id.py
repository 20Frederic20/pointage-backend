from dataclasses import dataclass

from core.application import Query

from ..dtos import AnomalyListItemDTO


@dataclass(frozen=True)
class GetAnomalyByIdQuery(Query):
    """One back-office row (same shape as the list items); ``None`` if unknown."""

    anomaly_id: str

    Result = AnomalyListItemDTO | None

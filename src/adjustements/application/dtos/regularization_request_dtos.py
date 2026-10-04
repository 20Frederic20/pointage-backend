from dataclasses import dataclass
from datetime import datetime

from adjustements import RegularizationStatus
from core.application import DTO


@dataclass(frozen=True)
class RegularizationRequestDTO(DTO):

    id: str
    anomaly_id: str
    request_at: datetime
    reason: str
    proposed_time: datetime
    status:RegularizationStatus
    decision_comment: str | None = None
    validated_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_aggregate(cls, regularization_request) -> "RegularizationRequestDTO":

        return cls(
            id=regularization_request.id.value,
            anomaly_id=regularization_request.anomaly_id.value,
            request_at=regularization_request.request_at,
            reason=regularization_request.reason,
            proposed_time=regularization_request.proposed_time,
            status=regularization_request.status,
            decision_comment=regularization_request.decision_comment,
            validated_at=regularization_request.validated_at,
            created_at=regularization_request.created_at,
            updated_at=regularization_request.updated_at,
        )


@dataclass(frozen=True)
class RegularizationRequestsPageDTO(DTO):
    items: tuple[RegularizationRequestDTO, ...]
    total: int
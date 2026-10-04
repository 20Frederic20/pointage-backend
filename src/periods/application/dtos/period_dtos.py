from dataclasses import dataclass
from datetime import date, datetime

from core.application import DTO

from ...domain.entities import Period


@dataclass(frozen=True)
class PeriodDTO(DTO):
    id: str
    start_date: date
    end_date: date
    status: str
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_aggregate(cls, period: Period) -> "PeriodDTO":
        return cls(
            id=period.id.value,
            start_date=period.start_date,
            end_date=period.end_date,
            status=period.status.value,
            closed_at=period.closed_at,
            created_at=period.created_at,
            updated_at=period.updated_at,
        )

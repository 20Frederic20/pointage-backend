from dataclasses import dataclass
from datetime import datetime, timedelta

from core.application import DTO

from ...domain.entities import Absence


@dataclass(frozen=True)
class AbsenceDTO(DTO):
    id: str
    employee_id: str
    absence_type_id: str
    start_at: datetime
    end_at: datetime
    duration: timedelta
    reason: str
    status: str
    justification_reference: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_aggregate(cls, absence: Absence) -> "AbsenceDTO":
        return cls(
            id=absence.id.value,
            employee_id=absence.employee_id.value,
            absence_type_id=absence.absence_type_id.value,
            start_at=absence.start_at,
            end_at=absence.end_at,
            duration=absence.duration,
            reason=absence.reason,
            status=absence.status.value,
            justification_reference=absence.justification_reference,
            created_at=absence.created_at,
            updated_at=absence.updated_at,
        )

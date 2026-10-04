from dataclasses import dataclass
from datetime import datetime

from core.application import DTO

from ...domain.entities import AbsenceType


@dataclass(frozen=True)
class AbsenceTypeDTO(DTO):
    id: str
    name: str
    paid: bool
    counts_as_work_time: bool
    deducts_balance: bool
    active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_aggregate(cls, absence_type: AbsenceType) -> "AbsenceTypeDTO":
        return cls(
            id=absence_type.id.value,
            name=absence_type.name,
            paid=absence_type.paid,
            counts_as_work_time=absence_type.counts_as_work_time,
            deducts_balance=absence_type.deducts_balance,
            active=absence_type.active,
            created_at=absence_type.created_at,
            updated_at=absence_type.updated_at,
        )

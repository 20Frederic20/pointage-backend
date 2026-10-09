from datetime import datetime

from core.domain.events import BaseEvent, decode_datetime, encode_datetime
from identity.domain.value_objects.ids import EmployeeId

from ..value_objects import AbsenceId, AbsenceStatus, AbsenceTypeId


class AbsenceDeclared(BaseEvent[AbsenceId]):
    """An employee declared an absence (pending until decided)."""

    def __init__(
        self,
        absence_id: AbsenceId,
        *,
        employee_id: EmployeeId,
        absence_type_id: AbsenceTypeId,
        start_at: datetime,
        end_at: datetime,
        reason: str,
        justification_reference: str | None,
    ) -> None:
        super().__init__()
        self.absence_id = absence_id
        self.employee_id = employee_id
        self.absence_type_id = absence_type_id
        self.start_at = start_at
        self.end_at = end_at
        self.reason = reason
        self.justification_reference = justification_reference

    def get_aggregate_id(self) -> AbsenceId:
        return self.absence_id

    def get_event_name(self) -> str:
        return "absences.absence.declared"

    def to_payload(self) -> dict:
        return {
            "absence_id": self.absence_id.value,
            "employee_id": self.employee_id.value,
            "absence_type_id": self.absence_type_id.value,
            "start_at": encode_datetime(self.start_at),
            "end_at": encode_datetime(self.end_at),
            "reason": self.reason,
            "justification_reference": self.justification_reference,
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "AbsenceDeclared":
        return cls(
            AbsenceId(payload["absence_id"]),
            employee_id=EmployeeId(payload["employee_id"]),
            absence_type_id=AbsenceTypeId(payload["absence_type_id"]),
            start_at=decode_datetime(payload["start_at"]),
            end_at=decode_datetime(payload["end_at"]),
            reason=payload["reason"],
            justification_reference=payload["justification_reference"],
        )


class AbsenceApproved(BaseEvent[AbsenceId]):
    """An absence was approved."""

    def __init__(self, absence_id: AbsenceId) -> None:
        super().__init__()
        self.absence_id = absence_id

    def get_aggregate_id(self) -> AbsenceId:
        return self.absence_id

    def get_event_name(self) -> str:
        return "absences.absence.approved"

    def to_payload(self) -> dict:
        return {"absence_id": self.absence_id.value}

    @classmethod
    def from_payload(cls, payload: dict) -> "AbsenceApproved":
        return cls(AbsenceId(payload["absence_id"]))


class AbsenceRejected(BaseEvent[AbsenceId]):
    """An absence was rejected."""

    def __init__(self, absence_id: AbsenceId) -> None:
        super().__init__()
        self.absence_id = absence_id

    def get_aggregate_id(self) -> AbsenceId:
        return self.absence_id

    def get_event_name(self) -> str:
        return "absences.absence.rejected"

    def to_payload(self) -> dict:
        return {"absence_id": self.absence_id.value}

    @classmethod
    def from_payload(cls, payload: dict) -> "AbsenceRejected":
        return cls(AbsenceId(payload["absence_id"]))


class AbsenceImported(BaseEvent[AbsenceId]):
    """An absence taken over from the state tables when event sourcing started."""

    def __init__(
        self,
        absence_id: AbsenceId,
        *,
        employee_id: EmployeeId,
        absence_type_id: AbsenceTypeId,
        start_at: datetime,
        end_at: datetime,
        reason: str,
        status: AbsenceStatus,
        justification_reference: str | None,
        created_at: datetime,
    ) -> None:
        super().__init__()
        self.absence_id = absence_id
        self.employee_id = employee_id
        self.absence_type_id = absence_type_id
        self.start_at = start_at
        self.end_at = end_at
        self.reason = reason
        self.status = status
        self.justification_reference = justification_reference
        self.created_at = created_at

    def get_aggregate_id(self) -> AbsenceId:
        return self.absence_id

    def get_event_name(self) -> str:
        return "absences.absence.imported"

    def to_payload(self) -> dict:
        return {
            "absence_id": self.absence_id.value,
            "employee_id": self.employee_id.value,
            "absence_type_id": self.absence_type_id.value,
            "start_at": encode_datetime(self.start_at),
            "end_at": encode_datetime(self.end_at),
            "reason": self.reason,
            "status": self.status.value,
            "justification_reference": self.justification_reference,
            "created_at": encode_datetime(self.created_at),
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "AbsenceImported":
        return cls(
            AbsenceId(payload["absence_id"]),
            employee_id=EmployeeId(payload["employee_id"]),
            absence_type_id=AbsenceTypeId(payload["absence_type_id"]),
            start_at=decode_datetime(payload["start_at"]),
            end_at=decode_datetime(payload["end_at"]),
            reason=payload["reason"],
            status=AbsenceStatus(payload["status"]),
            justification_reference=payload["justification_reference"],
            created_at=decode_datetime(payload["created_at"]),
        )

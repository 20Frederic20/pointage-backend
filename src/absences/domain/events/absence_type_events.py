from datetime import datetime

from core.domain.events import BaseEvent, decode_datetime, encode_datetime

from ..value_objects import AbsenceTypeId


class AbsenceTypeCreated(BaseEvent[AbsenceTypeId]):
    """A new (active) absence type was created."""

    def __init__(
        self,
        absence_type_id: AbsenceTypeId,
        *,
        name: str,
        paid: bool,
        counts_as_work_time: bool,
        deducts_balance: bool,
    ) -> None:
        super().__init__()
        self.absence_type_id = absence_type_id
        self.name = name
        self.paid = paid
        self.counts_as_work_time = counts_as_work_time
        self.deducts_balance = deducts_balance

    def get_aggregate_id(self) -> AbsenceTypeId:
        return self.absence_type_id

    def get_event_name(self) -> str:
        return "absences.absence_type.created"

    def to_payload(self) -> dict:
        return {
            "absence_type_id": self.absence_type_id.value,
            "name": self.name,
            "paid": self.paid,
            "counts_as_work_time": self.counts_as_work_time,
            "deducts_balance": self.deducts_balance,
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "AbsenceTypeCreated":
        return cls(
            AbsenceTypeId(payload["absence_type_id"]),
            name=payload["name"],
            paid=payload["paid"],
            counts_as_work_time=payload["counts_as_work_time"],
            deducts_balance=payload["deducts_balance"],
        )


class AbsenceTypeImported(BaseEvent[AbsenceTypeId]):
    """An absence type taken over from the state tables when event sourcing started."""

    def __init__(
        self,
        absence_type_id: AbsenceTypeId,
        *,
        name: str,
        paid: bool,
        counts_as_work_time: bool,
        deducts_balance: bool,
        active: bool,
        created_at: datetime,
    ) -> None:
        super().__init__()
        self.absence_type_id = absence_type_id
        self.name = name
        self.paid = paid
        self.counts_as_work_time = counts_as_work_time
        self.deducts_balance = deducts_balance
        self.active = active
        self.created_at = created_at

    def get_aggregate_id(self) -> AbsenceTypeId:
        return self.absence_type_id

    def get_event_name(self) -> str:
        return "absences.absence_type.imported"

    def to_payload(self) -> dict:
        return {
            "absence_type_id": self.absence_type_id.value,
            "name": self.name,
            "paid": self.paid,
            "counts_as_work_time": self.counts_as_work_time,
            "deducts_balance": self.deducts_balance,
            "active": self.active,
            "created_at": encode_datetime(self.created_at),
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "AbsenceTypeImported":
        return cls(
            AbsenceTypeId(payload["absence_type_id"]),
            name=payload["name"],
            paid=payload["paid"],
            counts_as_work_time=payload["counts_as_work_time"],
            deducts_balance=payload["deducts_balance"],
            active=payload["active"],
            created_at=decode_datetime(payload["created_at"]),
        )

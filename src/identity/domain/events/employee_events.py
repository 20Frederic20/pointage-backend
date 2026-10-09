from datetime import datetime

from core.domain.events import BaseEvent, decode_datetime, encode_datetime

from ..value_objects.ids import EmployeeId, UserId
from ..value_objects.role import Role


class EmployeeCreated(BaseEvent[EmployeeId]):

    def __init__(
        self,
        employee_id: EmployeeId,
        *,
        user_id: UserId,
        employee_number: str,
        is_active: bool,
        phone: str | None,
        role: Role,
    ) -> None:
        super().__init__()
        self.employee_id = employee_id
        self.user_id = user_id
        self.employee_number = employee_number
        self.is_active = is_active
        self.phone = phone
        self.role = role

    def get_aggregate_id(self) -> EmployeeId:
        return self.employee_id

    def get_event_name(self) -> str:
        return "users.employee.created"

    def to_payload(self) -> dict:
        return {
            "employee_id": self.employee_id.value,
            "user_id": self.user_id.value,
            "employee_number": self.employee_number,
            "is_active": self.is_active,
            "phone": self.phone,
            "role": self.role.value,
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "EmployeeCreated":
        return cls(
            EmployeeId(payload["employee_id"]),
            user_id=UserId(payload["user_id"]),
            employee_number=payload["employee_number"],
            is_active=payload["is_active"],
            phone=payload["phone"],
            role=Role(payload["role"]),
        )


class EmployeeUpdated(BaseEvent[EmployeeId]):
    """An employee record changed (the event holds the resulting values)."""

    def __init__(
        self,
        employee_id: EmployeeId,
        *,
        employee_number: str,
        is_active: bool,
        phone: str | None,
    ) -> None:
        super().__init__()
        self.employee_id = employee_id
        self.employee_number = employee_number
        self.is_active = is_active
        self.phone = phone

    def get_aggregate_id(self) -> EmployeeId:
        return self.employee_id

    def get_event_name(self) -> str:
        return "users.employee.updated"

    def to_payload(self) -> dict:
        return {
            "employee_id": self.employee_id.value,
            "employee_number": self.employee_number,
            "is_active": self.is_active,
            "phone": self.phone,
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "EmployeeUpdated":
        return cls(
            EmployeeId(payload["employee_id"]),
            employee_number=payload["employee_number"],
            is_active=payload["is_active"],
            phone=payload["phone"],
        )


class EmployeeImported(BaseEvent[EmployeeId]):
    """An employee taken over from the state tables when event sourcing started."""

    def __init__(
        self,
        employee_id: EmployeeId,
        *,
        user_id: UserId,
        employee_number: str,
        is_active: bool,
        phone: str | None,
        role: Role,
        created_at: datetime,
    ) -> None:
        super().__init__()
        self.employee_id = employee_id
        self.user_id = user_id
        self.employee_number = employee_number
        self.is_active = is_active
        self.phone = phone
        self.role = role
        self.created_at = created_at

    def get_aggregate_id(self) -> EmployeeId:
        return self.employee_id

    def get_event_name(self) -> str:
        return "users.employee.imported"

    def to_payload(self) -> dict:
        return {
            "employee_id": self.employee_id.value,
            "user_id": self.user_id.value,
            "employee_number": self.employee_number,
            "is_active": self.is_active,
            "phone": self.phone,
            "role": self.role.value,
            "created_at": encode_datetime(self.created_at),
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "EmployeeImported":
        return cls(
            EmployeeId(payload["employee_id"]),
            user_id=UserId(payload["user_id"]),
            employee_number=payload["employee_number"],
            is_active=payload["is_active"],
            phone=payload["phone"],
            role=Role(payload["role"]),
            created_at=decode_datetime(payload["created_at"]),
        )

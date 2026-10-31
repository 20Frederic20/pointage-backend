from datetime import datetime

from core.domain.events import BaseEvent, decode_datetime, encode_datetime

from ..value_objects.ids import DirectoryId, EmployeeId, UserId
from ..value_objects.role import Role


def _value(directory_id: DirectoryId | None) -> str | None:
    return directory_id.value if directory_id is not None else None


def _directory_id(value: str | None) -> DirectoryId | None:
    # Events stored before the company existed carry no key: None.
    return DirectoryId(value) if value is not None else None


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
        company_directory_id: DirectoryId | None = None,
    ) -> None:
        super().__init__()
        self.employee_id = employee_id
        self.user_id = user_id
        self.employee_number = employee_number
        self.is_active = is_active
        self.phone = phone
        self.role = role
        self.company_directory_id = company_directory_id

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
            "company_directory_id": _value(self.company_directory_id),
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
            company_directory_id=_directory_id(payload.get("company_directory_id")),
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
        company_directory_id: DirectoryId | None = None,
    ) -> None:
        super().__init__()
        self.employee_id = employee_id
        self.user_id = user_id
        self.employee_number = employee_number
        self.is_active = is_active
        self.phone = phone
        self.role = role
        self.created_at = created_at
        self.company_directory_id = company_directory_id

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
            "company_directory_id": _value(self.company_directory_id),
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
            company_directory_id=_directory_id(payload.get("company_directory_id")),
        )


class EmployeeRoleChanged(BaseEvent[EmployeeId]):
    """The role of an employee record changed (per company)."""

    def __init__(self, employee_id: EmployeeId, *, role: Role) -> None:
        super().__init__()
        self.employee_id = employee_id
        self.role = role

    def get_aggregate_id(self) -> EmployeeId:
        return self.employee_id

    def get_event_name(self) -> str:
        return "users.employee.role_changed"

    def to_payload(self) -> dict:
        return {"employee_id": self.employee_id.value, "role": self.role.value}

    @classmethod
    def from_payload(cls, payload: dict) -> "EmployeeRoleChanged":
        return cls(EmployeeId(payload["employee_id"]), role=Role(payload["role"]))


class _EmployeeStatusEvent(BaseEvent[EmployeeId]):
    """Base of the payload-less status changes of an employee record."""

    def __init__(self, employee_id: EmployeeId) -> None:
        super().__init__()
        self.employee_id = employee_id

    def get_aggregate_id(self) -> EmployeeId:
        return self.employee_id

    def to_payload(self) -> dict:
        return {"employee_id": self.employee_id.value}

    @classmethod
    def from_payload(cls, payload: dict):
        return cls(EmployeeId(payload["employee_id"]))


class EmployeeDeactivated(_EmployeeStatusEvent):
    """The employee record can no longer punch (leave, departure); its account is untouched."""

    def get_event_name(self) -> str:
        return "users.employee.deactivated"


class EmployeeActivated(_EmployeeStatusEvent):
    """The employee record can punch again."""

    def get_event_name(self) -> str:
        return "users.employee.activated"


class EmployeeCompanySet(BaseEvent[EmployeeId]):
    """The company (root directory) of an employee record, set by the backfill."""

    def __init__(self, employee_id: EmployeeId, *, company_directory_id: DirectoryId) -> None:
        super().__init__()
        self.employee_id = employee_id
        self.company_directory_id = company_directory_id

    def get_aggregate_id(self) -> EmployeeId:
        return self.employee_id

    def get_event_name(self) -> str:
        return "users.employee.company_set"

    def to_payload(self) -> dict:
        return {"employee_id": self.employee_id.value, "company_directory_id": self.company_directory_id.value}

    @classmethod
    def from_payload(cls, payload: dict) -> "EmployeeCompanySet":
        return cls(EmployeeId(payload["employee_id"]), company_directory_id=DirectoryId(payload["company_directory_id"]))

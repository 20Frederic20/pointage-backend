from datetime import date, datetime

from core.domain.events import BaseEvent, decode_date, decode_datetime, encode_date, encode_datetime

from ..value_objects.ids import DirectoryId, EmployeeAssignmentId, EmployeeId, SiteId


class EmployeeAssigned(BaseEvent[EmployeeAssignmentId]):
    """An employee was assigned to a directory and its site."""

    def __init__(
        self,
        employee_assignment_id: EmployeeAssignmentId,
        *,
        employee_id: EmployeeId,
        directory_id: DirectoryId,
        site_id: SiteId,
        start_date: date,
        end_date: date | None,
    ) -> None:
        super().__init__()
        self.employee_assignment_id = employee_assignment_id
        self.employee_id = employee_id
        self.directory_id = directory_id
        self.site_id = site_id
        self.start_date = start_date
        self.end_date = end_date

    def get_aggregate_id(self) -> EmployeeAssignmentId:
        return self.employee_assignment_id

    def get_event_name(self) -> str:
        return "users.employee_assignment.created"

    def to_payload(self) -> dict:
        return {
            "employee_assignment_id": self.employee_assignment_id.value,
            "employee_id": self.employee_id.value,
            "directory_id": self.directory_id.value,
            "site_id": self.site_id.value,
            "start_date": encode_date(self.start_date),
            "end_date": encode_date(self.end_date),
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "EmployeeAssigned":
        return cls(
            EmployeeAssignmentId(payload["employee_assignment_id"]),
            employee_id=EmployeeId(payload["employee_id"]),
            directory_id=DirectoryId(payload["directory_id"]),
            site_id=SiteId(payload["site_id"]),
            start_date=decode_date(payload["start_date"]),
            end_date=decode_date(payload["end_date"]),
        )


class EmployeeAssignmentEnded(BaseEvent[EmployeeAssignmentId]):
    """An employee assignment was given an end date."""

    def __init__(self, employee_assignment_id: EmployeeAssignmentId, *, end_date: date) -> None:
        super().__init__()
        self.employee_assignment_id = employee_assignment_id
        self.end_date = end_date

    def get_aggregate_id(self) -> EmployeeAssignmentId:
        return self.employee_assignment_id

    def get_event_name(self) -> str:
        return "users.employee_assignment.ended"

    def to_payload(self) -> dict:
        return {"employee_assignment_id": self.employee_assignment_id.value, "end_date": encode_date(self.end_date)}

    @classmethod
    def from_payload(cls, payload: dict) -> "EmployeeAssignmentEnded":
        return cls(
            EmployeeAssignmentId(payload["employee_assignment_id"]),
            end_date=decode_date(payload["end_date"]),
        )


class EmployeeAssignmentImported(BaseEvent[EmployeeAssignmentId]):
    """An assignment taken over from the state tables when event sourcing started."""

    def __init__(
        self,
        employee_assignment_id: EmployeeAssignmentId,
        *,
        employee_id: EmployeeId,
        directory_id: DirectoryId,
        site_id: SiteId,
        start_date: date,
        end_date: date | None,
        created_at: datetime,
    ) -> None:
        super().__init__()
        self.employee_assignment_id = employee_assignment_id
        self.employee_id = employee_id
        self.directory_id = directory_id
        self.site_id = site_id
        self.start_date = start_date
        self.end_date = end_date
        self.created_at = created_at

    def get_aggregate_id(self) -> EmployeeAssignmentId:
        return self.employee_assignment_id

    def get_event_name(self) -> str:
        return "users.employee_assignment.imported"

    def to_payload(self) -> dict:
        return {
            "employee_assignment_id": self.employee_assignment_id.value,
            "employee_id": self.employee_id.value,
            "directory_id": self.directory_id.value,
            "site_id": self.site_id.value,
            "start_date": encode_date(self.start_date),
            "end_date": encode_date(self.end_date),
            "created_at": encode_datetime(self.created_at),
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "EmployeeAssignmentImported":
        return cls(
            EmployeeAssignmentId(payload["employee_assignment_id"]),
            employee_id=EmployeeId(payload["employee_id"]),
            directory_id=DirectoryId(payload["directory_id"]),
            site_id=SiteId(payload["site_id"]),
            start_date=decode_date(payload["start_date"]),
            end_date=decode_date(payload["end_date"]),
            created_at=decode_datetime(payload["created_at"]),
        )


class EmployeeAssignmentCancelled(BaseEvent[EmployeeAssignmentId]):
    """A same-day transfer replaced this assignment: it never applies."""

    def __init__(self, employee_assignment_id: EmployeeAssignmentId) -> None:
        super().__init__()
        self.employee_assignment_id = employee_assignment_id

    def get_aggregate_id(self) -> EmployeeAssignmentId:
        return self.employee_assignment_id

    def get_event_name(self) -> str:
        return "users.employee_assignment.cancelled"

    def to_payload(self) -> dict:
        return {"employee_assignment_id": self.employee_assignment_id.value}

    @classmethod
    def from_payload(cls, payload: dict) -> "EmployeeAssignmentCancelled":
        return cls(EmployeeAssignmentId(payload["employee_assignment_id"]))

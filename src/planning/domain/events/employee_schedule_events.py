from datetime import date, datetime

from core.domain.events import BaseEvent, decode_date, decode_datetime, encode_date, encode_datetime
from identity.domain.value_objects.ids import EmployeeId

from ..value_objects import EmployeeScheduleId, TimeProfileVersionId


class EmployeeScheduleAssigned(BaseEvent[EmployeeScheduleId]):
    """A time profile version was assigned to an employee."""

    def __init__(
        self,
        employee_schedule_id: EmployeeScheduleId,
        *,
        employee_id: EmployeeId,
        time_profile_version_id: TimeProfileVersionId,
        start_date: date,
        end_date: date | None,
    ) -> None:
        super().__init__()
        self.employee_schedule_id = employee_schedule_id
        self.employee_id = employee_id
        self.time_profile_version_id = time_profile_version_id
        self.start_date = start_date
        self.end_date = end_date

    def get_aggregate_id(self) -> EmployeeScheduleId:
        return self.employee_schedule_id

    def get_event_name(self) -> str:
        return "planning.employee_schedule.assigned"

    def to_payload(self) -> dict:
        return {
            "employee_schedule_id": self.employee_schedule_id.value,
            "employee_id": self.employee_id.value,
            "time_profile_version_id": self.time_profile_version_id.value,
            "start_date": encode_date(self.start_date),
            "end_date": encode_date(self.end_date),
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "EmployeeScheduleAssigned":
        return cls(
            EmployeeScheduleId(payload["employee_schedule_id"]),
            employee_id=EmployeeId(payload["employee_id"]),
            time_profile_version_id=TimeProfileVersionId(payload["time_profile_version_id"]),
            start_date=decode_date(payload["start_date"]),
            end_date=decode_date(payload["end_date"]),
        )


class EmployeeScheduleEnded(BaseEvent[EmployeeScheduleId]):
    """An employee schedule was given an end date."""

    def __init__(self, employee_schedule_id: EmployeeScheduleId, *, end_date: date) -> None:
        super().__init__()
        self.employee_schedule_id = employee_schedule_id
        self.end_date = end_date

    def get_aggregate_id(self) -> EmployeeScheduleId:
        return self.employee_schedule_id

    def get_event_name(self) -> str:
        return "planning.employee_schedule.ended"

    def to_payload(self) -> dict:
        return {"employee_schedule_id": self.employee_schedule_id.value, "end_date": encode_date(self.end_date)}

    @classmethod
    def from_payload(cls, payload: dict) -> "EmployeeScheduleEnded":
        return cls(EmployeeScheduleId(payload["employee_schedule_id"]), end_date=decode_date(payload["end_date"]))


class EmployeeScheduleImported(BaseEvent[EmployeeScheduleId]):
    """An employee schedule taken over from the state tables when event sourcing started."""

    def __init__(
        self,
        employee_schedule_id: EmployeeScheduleId,
        *,
        employee_id: EmployeeId,
        time_profile_version_id: TimeProfileVersionId,
        start_date: date,
        end_date: date | None,
        created_at: datetime,
    ) -> None:
        super().__init__()
        self.employee_schedule_id = employee_schedule_id
        self.employee_id = employee_id
        self.time_profile_version_id = time_profile_version_id
        self.start_date = start_date
        self.end_date = end_date
        self.created_at = created_at

    def get_aggregate_id(self) -> EmployeeScheduleId:
        return self.employee_schedule_id

    def get_event_name(self) -> str:
        return "planning.employee_schedule.imported"

    def to_payload(self) -> dict:
        return {
            "employee_schedule_id": self.employee_schedule_id.value,
            "employee_id": self.employee_id.value,
            "time_profile_version_id": self.time_profile_version_id.value,
            "start_date": encode_date(self.start_date),
            "end_date": encode_date(self.end_date),
            "created_at": encode_datetime(self.created_at),
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "EmployeeScheduleImported":
        return cls(
            EmployeeScheduleId(payload["employee_schedule_id"]),
            employee_id=EmployeeId(payload["employee_id"]),
            time_profile_version_id=TimeProfileVersionId(payload["time_profile_version_id"]),
            start_date=decode_date(payload["start_date"]),
            end_date=decode_date(payload["end_date"]),
            created_at=decode_datetime(payload["created_at"]),
        )

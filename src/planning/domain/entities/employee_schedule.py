from datetime import date, datetime

from core.domain.entity import AggregateRoot
from identity.domain import EmployeeId

from ..errors import InvalidScheduleDatesError
from ..events import EmployeeScheduleAssigned, EmployeeScheduleEnded
from ..value_objects import EmployeeScheduleId, TimeProfileVersionId


class EmployeeSchedule(AggregateRoot[EmployeeScheduleId]):
    """An employee works under a time profile version from ``start_date`` to ``end_date``."""

    __slots__ = ("_employee_id", "_end_date", "_start_date", "_time_profile_version_id")

    def __init__(
        self,
        employee_schedule_id: EmployeeScheduleId,
        *,
        employee_id: EmployeeId,
        time_profile_version_id: TimeProfileVersionId,
        start_date: date,
        end_date: date | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        version: int = 0,
    ) -> None:
        super().__init__(employee_schedule_id, created_at=created_at, updated_at=updated_at, version=version)
        _check_dates(start_date, end_date, employee_schedule_id)
        self._employee_id = employee_id
        self._time_profile_version_id = time_profile_version_id
        self._start_date = start_date
        self._end_date = end_date

    @classmethod
    def assign(
        cls,
        employee_schedule_id: EmployeeScheduleId,
        *,
        employee_id: EmployeeId,
        time_profile_version_id: TimeProfileVersionId,
        start_date: date,
        end_date: date | None = None,
    ) -> "EmployeeSchedule":
        schedule = cls(
            employee_schedule_id,
            employee_id=employee_id,
            time_profile_version_id=time_profile_version_id,
            start_date=start_date,
            end_date=end_date,
        )
        schedule.record_event(EmployeeScheduleAssigned(employee_schedule_id))
        return schedule

    def is_applicable(self, day: date) -> bool:
        """``estApplicable``."""
        return self._start_date <= day and (self._end_date is None or day <= self._end_date)

    def end(self, end_date: date) -> None:
        """``terminer``: the schedule's last day is ``end_date``."""
        _check_dates(self._start_date, end_date, self.id)
        self._end_date = end_date
        self.touch()
        self.record_event(EmployeeScheduleEnded(self.id))

    @property
    def employee_id(self) -> EmployeeId:
        return self._employee_id

    @property
    def time_profile_version_id(self) -> TimeProfileVersionId:
        return self._time_profile_version_id

    @property
    def start_date(self) -> date:
        return self._start_date

    @property
    def end_date(self) -> date | None:
        return self._end_date


def _check_dates(start_date: date, end_date: date | None, schedule_id: EmployeeScheduleId) -> None:
    if end_date is not None and end_date < start_date:
        raise InvalidScheduleDatesError(
            f"Schedule ends ({end_date}) before it starts ({start_date})",
            context=schedule_id.value,
        )

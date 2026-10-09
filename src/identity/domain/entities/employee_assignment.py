"""The EmployeeAssignment aggregate — where an employee works, and when."""

from datetime import date, datetime
from typing import Self

from core.domain.entity import AggregateRoot

from ..errors.errors import InvalidEmployeeAssignmentDatesError
from ..events.employee_assignment_events import (
    EmployeeAssigned,
    EmployeeAssignmentEnded,
    EmployeeAssignmentImported,
)
from ..value_objects.ids import DirectoryId, EmployeeAssignmentId, EmployeeId, SiteId


class EmployeeAssignment(AggregateRoot[EmployeeAssignmentId]):
    """An employee belongs to a directory from ``start_date`` to ``end_date``
    (inclusive; open-ended when ``end_date`` is ``None``).

    ``site_id`` is the precise site of that directory where the employee
    works — principal or annex — and the one their punches are checked
    against.
    """

    __slots__ = ("_directory_id", "_employee_id", "_end_date", "_site_id", "_start_date")

    def __init__(
        self,
        employee_assignment_id: EmployeeAssignmentId,
        *,
        employee_id: EmployeeId,
        directory_id: DirectoryId,
        site_id: SiteId,
        start_date: date,
        end_date: date | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        version: int = 0,
    ) -> None:
        super().__init__(
            employee_assignment_id, created_at=created_at, updated_at=updated_at, version=version
        )
        _check_dates(start_date, end_date, employee_assignment_id)
        self._employee_id = employee_id
        self._directory_id = directory_id
        self._site_id = site_id
        self._start_date = start_date
        self._end_date = end_date

    @classmethod
    def assign(
        cls,
        employee_assignment_id: EmployeeAssignmentId,
        *,
        employee_id: EmployeeId,
        directory_id: DirectoryId,
        site_id: SiteId,
        start_date: date,
        end_date: date | None = None,
    ) -> Self:
        """Factory for a brand-new assignment; records :class:`EmployeeAssigned`."""
        _check_dates(start_date, end_date, employee_assignment_id)
        assignment = cls.rehydrate(employee_assignment_id, [])
        assignment._raise(
            EmployeeAssigned(
                employee_assignment_id,
                employee_id=employee_id,
                directory_id=directory_id,
                site_id=site_id,
                start_date=start_date,
                end_date=end_date,
            )
        )
        return assignment

    def is_active_on(self, day: date) -> bool:
        """``estActive(date)``."""
        return self._start_date <= day and (self._end_date is None or day <= self._end_date)

    def end(self, end_date: date) -> None:
        """``terminer``: the assignment's last day is ``end_date``."""
        _check_dates(self._start_date, end_date, self.id)
        self._raise(EmployeeAssignmentEnded(self.id, end_date=end_date))

    def _apply(self, event) -> None:
        match event:
            case EmployeeAssigned() | EmployeeAssignmentImported():
                self._employee_id = event.employee_id
                self._directory_id = event.directory_id
                self._site_id = event.site_id
                self._start_date = event.start_date
                self._end_date = event.end_date
                if isinstance(event, EmployeeAssignmentImported):
                    self._created_at = event.created_at
            case EmployeeAssignmentEnded():
                self._end_date = event.end_date
            case _:
                super()._apply(event)

    @property
    def employee_id(self) -> EmployeeId:
        return self._employee_id

    @property
    def directory_id(self) -> DirectoryId:
        return self._directory_id

    @property
    def site_id(self) -> SiteId:
        return self._site_id

    @property
    def start_date(self) -> date:
        return self._start_date

    @property
    def end_date(self) -> date | None:
        return self._end_date


def _check_dates(
    start_date: date, end_date: date | None, employee_assignment_id: EmployeeAssignmentId
) -> None:
    if end_date is not None and end_date < start_date:
        raise InvalidEmployeeAssignmentDatesError(
            f"Assignment ends ({end_date}) before it starts ({start_date})",
            context=employee_assignment_id.value,
        )

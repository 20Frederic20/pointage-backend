from core.domain.events import BaseEvent

from ..value_objects import EmployeeScheduleId


class EmployeeScheduleAssigned(BaseEvent[EmployeeScheduleId]):
    """A time profile version was assigned to an employee."""

    def __init__(self, employee_schedule_id: EmployeeScheduleId) -> None:
        super().__init__()
        self._employee_schedule_id = employee_schedule_id

    def get_aggregate_id(self) -> EmployeeScheduleId:
        return self._employee_schedule_id

    def get_event_name(self) -> str:
        return "planning.employee_schedule.assigned"


class EmployeeScheduleEnded(BaseEvent[EmployeeScheduleId]):
    """An employee schedule was given an end date."""

    def __init__(self, employee_schedule_id: EmployeeScheduleId) -> None:
        super().__init__()
        self._employee_schedule_id = employee_schedule_id

    def get_aggregate_id(self) -> EmployeeScheduleId:
        return self._employee_schedule_id

    def get_event_name(self) -> str:
        return "planning.employee_schedule.ended"

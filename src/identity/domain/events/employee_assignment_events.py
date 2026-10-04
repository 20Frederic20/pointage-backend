from core.domain.events import BaseEvent

from ..value_objects.ids import EmployeeAssignmentId


class EmployeeAssigned(BaseEvent[EmployeeAssignmentId]):
    """An employee was assigned to a directory and its site."""

    def __init__(self, employee_assignment_id: EmployeeAssignmentId) -> None:
        super().__init__()
        self._employee_assignment_id = employee_assignment_id

    def get_aggregate_id(self) -> EmployeeAssignmentId:
        return self._employee_assignment_id

    def get_event_name(self) -> str:
        return "users.employee_assignment.created"


class EmployeeAssignmentEnded(BaseEvent[EmployeeAssignmentId]):
    """An employee assignment was given an end date."""

    def __init__(self, employee_assignment_id: EmployeeAssignmentId) -> None:
        super().__init__()
        self._employee_assignment_id = employee_assignment_id

    def get_aggregate_id(self) -> EmployeeAssignmentId:
        return self._employee_assignment_id

    def get_event_name(self) -> str:
        return "users.employee_assignment.ended"

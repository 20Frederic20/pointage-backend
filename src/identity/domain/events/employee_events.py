from core.domain.events import BaseEvent
from identity.domain import EmployeeId


class EmployeeCreated(BaseEvent[EmployeeId]):

    def __init__(self, employee_id: EmployeeId) -> None:
        super().__init__()
        self._employee_id = employee_id

    def get_aggregate_id(self) -> EmployeeId:
        return self._employee_id

    def get_event_name(self) -> str:
        return "users.employee.created"
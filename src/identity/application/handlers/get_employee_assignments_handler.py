"""List an employee's assignments, most recent first."""

from core.application import QueryHandler

from ...domain.repositories import IEmployeeAssignmentRepository
from ...domain.value_objects.ids import EmployeeId
from ..dtos import EmployeeAssignmentDTO
from ..queries import GetEmployeeAssignmentsQuery


class GetEmployeeAssignmentsHandler(
    QueryHandler[GetEmployeeAssignmentsQuery, tuple[EmployeeAssignmentDTO, ...]]
):
    def __init__(self, *, employee_assignment_repository: IEmployeeAssignmentRepository) -> None:
        super().__init__()
        self._assignments = employee_assignment_repository

    async def handle(self, request: GetEmployeeAssignmentsQuery) -> tuple[EmployeeAssignmentDTO, ...]:
        assignments = await self._assignments.find_by_employee(EmployeeId(request.employee_id))
        return tuple(EmployeeAssignmentDTO.from_aggregate(a) for a in assignments)

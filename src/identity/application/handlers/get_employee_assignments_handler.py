"""List an employee's assignments, most recent first, with site and directory names."""

from core.application import QueryHandler
from core.domain.errors import NotFoundError

from ...domain.repositories import IEmployeeAssignmentRepository
from ...domain.value_objects.ids import EmployeeId
from ..dtos import EmployeeAssignmentDTO
from ..queries import GetEmployeeAssignmentsQuery


class GetEmployeeAssignmentsHandler(
    QueryHandler[GetEmployeeAssignmentsQuery, tuple[EmployeeAssignmentDTO, ...]]
):
    def __init__(
        self,
        *,
        employee_assignment_repository: IEmployeeAssignmentRepository,
        site_repository=None,
        directory_repository=None,
    ) -> None:
        super().__init__()
        self._assignments = employee_assignment_repository
        self._sites = site_repository
        self._directories = directory_repository

    async def handle(self, request: GetEmployeeAssignmentsQuery) -> tuple[EmployeeAssignmentDTO, ...]:
        assignments = await self._assignments.find_by_employee(EmployeeId(request.employee_id))
        return tuple([
            EmployeeAssignmentDTO.from_aggregate(
                a,
                site_name=await _name(self._sites, a.site_id),
                directory_name=await _name(self._directories, a.directory_id),
            )
            for a in assignments
        ])


async def _name(repository, entity_id) -> str | None:
    """The entity's name; ``None`` when the read model lags or no repository is wired."""
    if repository is None:
        return None
    try:
        return (await repository.get_by_id(entity_id)).name
    except NotFoundError:
        return None

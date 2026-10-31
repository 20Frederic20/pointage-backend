"""What the screens show next to an employee record: names, company, current site."""

from dataclasses import replace
from datetime import UTC, datetime

from core.domain.errors import NotFoundError

from ...domain.entities import Employee
from ..dtos import EmployeeDTO


class EmployeeEnricher:
    """Read-side lookups (any repository may be ``None`` when a context does not wire it).

    ponytail: a few lookups per item on a 20-item page; batch them if pages grow.
    """

    def __init__(self, *, user_repository=None, directory_repository=None, employee_assignment_repository=None,
                 site_repository=None) -> None:
        self._users = user_repository
        self._directories = directory_repository
        self._assignments = employee_assignment_repository
        self._sites = site_repository

    async def to_dto(self, employee: Employee) -> EmployeeDTO:
        dto = EmployeeDTO.from_aggregate(employee)
        user = await _get(self._users, employee.user_id)
        company = await _get(self._directories, employee.company_directory_id)
        assignment = None
        if self._assignments is not None:
            assignment = await self._assignments.find_active(employee.id, datetime.now(UTC).date())
        site = await _get(self._sites, assignment.site_id if assignment else None)
        return replace(
            dto,
            first_name=user.first_name if user else None,
            last_name=user.last_name if user else None,
            company_name=company.name if company else None,
            current_site_id=assignment.site_id.value if assignment else None,
            current_site_name=site.name if site else None,
            current_assignment_end_date=assignment.end_date if assignment else None,
        )


async def _get(repository, entity_id):
    if repository is None or entity_id is None:
        return None
    try:
        return await repository.get_by_id(entity_id)
    except NotFoundError:
        return None

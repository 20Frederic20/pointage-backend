"""Before an assisted punch: confirm the typed employee number by its name."""

from core.application import QueryHandler
from core.audit import audit
from core.domain.errors import NotFoundError
from identity.domain import UserId
from identity.domain.repositories import IEmployeeRepository, IUserRepository
from punch.application.dtos import EmployeeLookupDTO
from punch.application.queries.lookup_employee import LookupEmployeeQuery
from punch.domain.errors import SelfAssistedPunchError


class LookupEmployeeHandler(QueryHandler[LookupEmployeeQuery, EmployeeLookupDTO]):
    """Active employees only (an inactive one is "unknown": no name leaks); never the caller."""

    def __init__(self, *, employee_repository: IEmployeeRepository, user_repository: IUserRepository) -> None:
        super().__init__()
        self.employee_repository = employee_repository
        self.user_repository = user_repository

    async def handle(self, request: LookupEmployeeQuery) -> EmployeeLookupDTO:
        employee = await self.employee_repository.find_by_employee_number(request.employee_number)
        if employee is None or not employee.is_active:
            audit.warning("action=PUNCH_ASSISTED_LOOKUP user_id=%s employee=%s status=FAIL reason=unknown_employee", request.actor_user_id, request.employee_number)
            raise NotFoundError("No active employee with this number", context=request.employee_number)
        if employee.user_id == UserId(request.actor_user_id):
            raise SelfAssistedPunchError("The assisted punch is for a colleague, not for yourself", context=employee.id.value)
        try:
            user = await self.user_repository.get_by_id(employee.user_id)
        except NotFoundError:
            return EmployeeLookupDTO(employee_number=employee.employee_number, first_name=None, last_name=None)
        return EmployeeLookupDTO(
            employee_number=employee.employee_number, first_name=user.first_name, last_name=user.last_name
        )

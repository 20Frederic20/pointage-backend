"""Edit an employee record under the role ceiling."""

from collections.abc import Sequence

from core.application import CommandHandler, IUnitOfWork
from core.application.outbox import IEventOutbox
from core.domain.entity import AggregateRoot

from ...domain.entities import Employee, User
from ...domain.errors import RoleCeilingError
from ...domain.value_objects.ids import EmployeeId
from ..commands import EditEmployeeCommand
from ..dtos import EmployeeDTO
from ..services import ensure_can_grant, ensure_can_manage, ensure_responsible


class EditEmployeeHandler(CommandHandler[EditEmployeeCommand, EmployeeDTO]):
    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        employee_repository,
        user_repository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._employees = employee_repository
        self._users = user_repository

    async def _execute(self, request: EditEmployeeCommand) -> tuple[EmployeeDTO, Sequence[AggregateRoot]]:
        actor_role = ensure_responsible(request.actor_role)
        employee = await self._employees.get_by_id(EmployeeId(request.employee_id))
        ensure_can_manage(actor_role, employee.role)
        if request.role is not None and request.role != employee.role:
            if employee.user_id.value == request.actor_user_id:
                raise RoleCeilingError("Nobody changes their own role", context=employee.id.value)
            ensure_can_grant(actor_role, request.role)
            employee.change_role(request.role)
        employee.change_phone(request.phone)

        user = await self._users.get_by_id(employee.user_id)
        user.update_profile(first_name=request.first_name, last_name=request.last_name)
        return EmployeeDTO.from_aggregate(employee), [user, employee]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, Employee):
            await self._employees.save(aggregate)
        elif isinstance(aggregate, User):
            await self._users.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")

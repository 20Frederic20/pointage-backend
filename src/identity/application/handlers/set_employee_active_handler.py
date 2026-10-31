"""Deactivate or reactivate an employee record; the account stays usable elsewhere."""

from collections.abc import Sequence

from core.application import CommandHandler, IUnitOfWork
from core.application.outbox import IEventOutbox
from core.domain.entity import AggregateRoot

from ...domain.entities import Employee
from ...domain.errors import AlreadyActiveInCompanyError, SelfDeactivationError
from ...domain.value_objects.ids import EmployeeId
from ..commands import SetEmployeeActiveCommand
from ..dtos import EmployeeDTO
from ..services import ensure_can_manage, ensure_responsible


class SetEmployeeActiveHandler(CommandHandler[SetEmployeeActiveCommand, EmployeeDTO]):
    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        employee_repository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._employees = employee_repository

    async def _execute(self, request: SetEmployeeActiveCommand) -> tuple[EmployeeDTO, Sequence[AggregateRoot]]:
        actor_role = ensure_responsible(request.actor_role)
        employee = await self._employees.get_by_id(EmployeeId(request.employee_id))
        ensure_can_manage(actor_role, employee.role)
        if request.active:
            await self._ensure_single_active_in_company(employee)
            employee.activate()
        else:
            if employee.user_id.value == request.actor_user_id:
                raise SelfDeactivationError("Nobody deactivates their own record", context=employee.id.value)
            employee.deactivate()
        return EmployeeDTO.from_aggregate(employee), [employee]

    async def _ensure_single_active_in_company(self, employee: Employee) -> None:
        for other in await self._employees.find_all_by_user_id(employee.user_id):
            if (
                other.id != employee.id
                and other.is_active
                and other.company_directory_id == employee.company_directory_id
            ):
                raise AlreadyActiveInCompanyError(
                    "This person already has an active record in this company", context=other.id.value
                )

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, Employee):
            await self._employees.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")

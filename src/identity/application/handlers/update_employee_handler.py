"""Profile edits — the handler only sees id + fields; who may edit is a
route-level guard (self or ADMIN)."""

from collections.abc import Sequence

from core.application import CommandHandler, IUnitOfWork
from core.application.outbox import IEventOutbox
from core.domain.entity import AggregateRoot

from ...domain.entities import Employee
from ...domain.repositories import IEmployeeRepository
from ...domain.value_objects.ids import EmployeeId
from ..commands import UpdateEmployeeCommand
from ..dtos import EmployeeDTO


class UpdateEmployeeHandler(
    CommandHandler[UpdateEmployeeCommand, EmployeeDTO]
):
    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        employee_repository: IEmployeeRepository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._employees = employee_repository

    async def _execute(
        self, request: UpdateEmployeeCommand
    ) -> tuple[EmployeeDTO, Sequence[AggregateRoot]]:
        employee = await self._employees.get_by_id(EmployeeId(request.employee_id))

        employee.update(
            employee_number=request.employee_number,
            is_active=request.is_active,
            phone=request.phone
        )
        return EmployeeDTO.from_aggregate(employee), [employee]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, Employee):
            await self._employees.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
"""Renaming the employee."""

from collections.abc import Sequence

from core.application import CommandHandler, IUnitOfWork
from core.application.outbox import IEventOutbox
from core.domain.entity import AggregateRoot
from identity.domain import EmployeeId
from identity.domain.errors.errors import EmployeeWithThisNumberAlreadyExistsError

from ...domain.entities import Employee
from ...domain.repositories import IEmployeeRepository
from ..commands import CreateEmployeeCommand
from ..dtos import EmployeeDTO


class CreateEmployeeHandler(
    CommandHandler[CreateEmployeeCommand, EmployeeDTO]
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
        self, request: CreateEmployeeCommand
    ) -> tuple[EmployeeDTO, Sequence[AggregateRoot]]:
        employee = await self._employees.exists_by_employee_number(request.employee_number)
        if employee:
            raise EmployeeWithThisNumberAlreadyExistsError(
                "Une entité portant le même code existe déjà"
            )
        employee = Employee.create(
            employee_id=EmployeeId.generate(),
            employee_number=request.employee_number,
            user_id=request.user_id,
            directory_id=request.directory_id,
            phone=request.phone,
            role=request.role,
            is_active=request.is_active
        )
        return EmployeeDTO.from_aggregate(employee), [employee]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, Employee):
            await self._employees.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")

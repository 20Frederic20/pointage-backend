"""Assign a time profile version to an employee."""

from collections.abc import Sequence

from core.application import CommandHandler, IEventOutbox, IUnitOfWork
from core.domain.entity import AggregateRoot
from core.domain.errors import NotFoundError
from identity.domain import EmployeeId
from identity.domain.repositories import IEmployeeRepository

from ...domain.entities import EmployeeSchedule
from ...domain.errors import OverlappingEmployeeScheduleError, TimeProfileVersionNotFoundError
from ...domain.repositories import IEmployeeScheduleRepository, ITimeProfileRepository
from ...domain.value_objects import EmployeeScheduleId, TimeProfileVersionId
from ..commands import AssignEmployeeScheduleCommand
from ..dtos import EmployeeScheduleDTO


class AssignEmployeeScheduleHandler(CommandHandler[AssignEmployeeScheduleCommand, EmployeeScheduleDTO]):
    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        employee_schedule_repository: IEmployeeScheduleRepository,
        time_profile_repository: ITimeProfileRepository,
        employee_repository: IEmployeeRepository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._schedules = employee_schedule_repository
        self._time_profiles = time_profile_repository
        self._employees = employee_repository

    async def _execute(
        self, request: AssignEmployeeScheduleCommand
    ) -> tuple[EmployeeScheduleDTO, Sequence[AggregateRoot]]:
        employee_id = EmployeeId(request.employee_id)
        if not await self._employees.exists(employee_id):
            raise NotFoundError(f"Employee {employee_id.value} not found", context=employee_id.value)

        version_id = TimeProfileVersionId(request.time_profile_version_id)
        if await self._time_profiles.find_by_version_id(version_id) is None:
            raise TimeProfileVersionNotFoundError(
                f"Time profile version {version_id.value} not found", context=version_id.value
            )
        if await self._schedules.exists_overlapping(employee_id, request.start_date, request.end_date):
            raise OverlappingEmployeeScheduleError(
                f"Employee {employee_id.value} already has a schedule in this date range",
                context=employee_id.value,
            )

        schedule = EmployeeSchedule.assign(
            EmployeeScheduleId.generate(),
            employee_id=employee_id,
            time_profile_version_id=version_id,
            start_date=request.start_date,
            end_date=request.end_date,
        )
        return EmployeeScheduleDTO.from_aggregate(schedule), [schedule]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, EmployeeSchedule):
            await self._schedules.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")

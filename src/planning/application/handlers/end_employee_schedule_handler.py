"""Set the last day of an employee schedule (``terminer``)."""

from collections.abc import Sequence

from core.application import CommandHandler, IEventOutbox, IUnitOfWork
from core.domain.entity import AggregateRoot

from ...domain.entities import EmployeeSchedule
from ...domain.errors import OverlappingEmployeeScheduleError
from ...domain.repositories import IEmployeeScheduleRepository
from ...domain.value_objects import EmployeeScheduleId
from ..commands import EndEmployeeScheduleCommand
from ..dtos import EmployeeScheduleDTO


class EndEmployeeScheduleHandler(CommandHandler[EndEmployeeScheduleCommand, EmployeeScheduleDTO]):
    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        employee_schedule_repository: IEmployeeScheduleRepository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._schedules = employee_schedule_repository

    async def _execute(
        self, request: EndEmployeeScheduleCommand
    ) -> tuple[EmployeeScheduleDTO, Sequence[AggregateRoot]]:
        schedule = await self._schedules.get_by_id(EmployeeScheduleId(request.employee_schedule_id))
        if await self._schedules.exists_overlapping(
            schedule.employee_id, schedule.start_date, request.end_date, excluding=schedule.id
        ):
            raise OverlappingEmployeeScheduleError(
                f"Employee {schedule.employee_id.value} already has a schedule in this date range",
                context=schedule.employee_id.value,
            )
        schedule.end(request.end_date)
        return EmployeeScheduleDTO.from_aggregate(schedule), [schedule]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, EmployeeSchedule):
            await self._schedules.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")

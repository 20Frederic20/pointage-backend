"""Event-store adapter for the EmployeeSchedule aggregate (write side)."""

from datetime import date

from sqlalchemy import select

from core.domain.errors import NotFoundError
from core.domain.events import encode_date
from core.infrastructure.event_store import EventModel, EventStore
from identity.domain import EmployeeId

from ...domain.entities import EmployeeSchedule
from ...domain.events import EmployeeScheduleAssigned, EmployeeScheduleEnded, EmployeeScheduleImported
from ...domain.repositories import IEmployeeScheduleRepository
from ...domain.value_objects import EmployeeScheduleId

EMPLOYEE_SCHEDULE_STREAM = "planning.employee_schedule"

EMPLOYEE_SCHEDULE_EVENT_TYPES = {
    "planning.employee_schedule.assigned": EmployeeScheduleAssigned,
    "planning.employee_schedule.ended": EmployeeScheduleEnded,
    "planning.employee_schedule.imported": EmployeeScheduleImported,
}


class EventSourcedEmployeeScheduleRepository(IEmployeeScheduleRepository):
    """A schedule is the replay of its stream.

    The employee and the start date never change after the first event, so
    candidates are selected on that event's payload, then filtered on the
    current end date in Python.
    """

    def __init__(self, event_store: EventStore) -> None:
        self._store = event_store

    async def get_by_id(self, employee_schedule_id: EmployeeScheduleId) -> EmployeeSchedule:
        events = await self._store.load(employee_schedule_id.value, EMPLOYEE_SCHEDULE_EVENT_TYPES)
        if not events:
            raise NotFoundError(
                f"Employee schedule {employee_schedule_id.value} not found",
                context=employee_schedule_id.value,
            )
        return EmployeeSchedule.rehydrate(employee_schedule_id, events)

    async def exists(self, employee_schedule_id: EmployeeScheduleId) -> bool:
        return await self._store.exists(employee_schedule_id.value, EMPLOYEE_SCHEDULE_STREAM)

    async def exists_overlapping(
        self,
        employee_id: EmployeeId,
        start_date: date,
        end_date: date | None,
        *,
        excluding: EmployeeScheduleId | None = None,
    ) -> bool:
        return any(
            schedule.id != excluding for schedule in await self._overlapping(employee_id, start_date, end_date)
        )

    async def find_applicable(self, employee_id: EmployeeId, day: date) -> EmployeeSchedule | None:
        return next(iter(await self._overlapping(employee_id, day, day)), None)

    async def find_employee_ids_between(self, start_date: date, end_date: date) -> list[EmployeeId]:
        schedules = await self._overlapping(None, start_date, end_date)
        return list(dict.fromkeys(schedule.employee_id for schedule in schedules))

    async def _overlapping(
        self, employee_id: EmployeeId | None, start_date: date, end_date: date | None
    ) -> list[EmployeeSchedule]:
        """Schedules whose ``[start_date, end_date]`` intersects the range (open end = forever), oldest first."""
        statement = select(EventModel.stream_id).where(
            EventModel.stream_type == EMPLOYEE_SCHEDULE_STREAM, EventModel.stream_version == 1
        )
        if employee_id is not None:
            statement = statement.where(EventModel.payload.contains({"employee_id": employee_id.value}))
        if end_date is not None:
            statement = statement.where(EventModel.payload["start_date"].astext <= encode_date(end_date))
        stream_ids = list((await self._store.session.scalars(statement.order_by(EventModel.global_position))).all())
        streams = await self._store.load_streams(stream_ids, EMPLOYEE_SCHEDULE_EVENT_TYPES)
        schedules = [
            EmployeeSchedule.rehydrate(EmployeeScheduleId(stream_id), events) for stream_id, events in streams.items()
        ]
        return [s for s in schedules if s.end_date is None or s.end_date >= start_date]

    async def save(self, employee_schedule: EmployeeSchedule) -> None:
        events = employee_schedule.domain_events
        await self._store.append(
            stream_type=EMPLOYEE_SCHEDULE_STREAM,
            stream_id=employee_schedule.id.value,
            expected_version=employee_schedule.version,
            events=events,
        )
        employee_schedule._advance_version(len(events))

    async def delete(self, employee_schedule_id: EmployeeScheduleId) -> None:
        raise NotImplementedError("Event-sourced employee schedules are never deleted")

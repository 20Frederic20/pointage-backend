"""Event-store adapter for the DailyTimeResult aggregate (write side)."""

from datetime import date

from core.domain.errors import NotFoundError
from core.domain.events import encode_date
from core.infrastructure.event_store import EventStore
from identity.domain import EmployeeId

from ...domain.entities import DailyTimeResult
from ...domain.events import DailyTimeResultCalculated, DailyTimeResultImported, DailyTimeResultValidated
from ...domain.repositories import IDailyTimeResultRepository
from ...domain.value_objects import DailyTimeResultId

DAILY_TIME_RESULT_STREAM = "time_calculation.daily_time_result"

DAILY_TIME_RESULT_EVENT_TYPES = {
    "time_calculation.daily_time_result.calculated": DailyTimeResultCalculated,
    "time_calculation.daily_time_result.validated": DailyTimeResultValidated,
    "time_calculation.daily_time_result.imported": DailyTimeResultImported,
}

EMPLOYEE_WORK_DATE_SCOPE = "time_calculation.daily_time_result.employee_id_work_date"


def _employee_work_date_key(employee_id: EmployeeId, work_date: date) -> str:
    return f"{employee_id.value}|{encode_date(work_date)}"


class EventSourcedDailyTimeResultRepository(IDailyTimeResultRepository):
    """A daily result is the replay of its stream; (employee, work date) is a unique key."""

    def __init__(self, event_store: EventStore) -> None:
        self._store = event_store

    async def get_by_id(self, daily_time_result_id: DailyTimeResultId) -> DailyTimeResult:
        events = await self._store.load(daily_time_result_id.value, DAILY_TIME_RESULT_EVENT_TYPES)
        if not events:
            raise NotFoundError(
                f"Daily time result {daily_time_result_id.value} not found",
                context=daily_time_result_id.value,
            )
        return DailyTimeResult.rehydrate(daily_time_result_id, events)

    async def exists(self, daily_time_result_id: DailyTimeResultId) -> bool:
        return await self._store.exists(daily_time_result_id.value, DAILY_TIME_RESULT_STREAM)

    async def find_by_employee_and_date(self, employee_id: EmployeeId, work_date: date) -> DailyTimeResult | None:
        stream_id = await self._store.owner(EMPLOYEE_WORK_DATE_SCOPE, _employee_work_date_key(employee_id, work_date))
        return await self.get_by_id(DailyTimeResultId(stream_id)) if stream_id is not None else None

    async def save(self, daily_time_result: DailyTimeResult) -> None:
        events = daily_time_result.domain_events
        stream_id = daily_time_result.id.value
        for event in events:
            # Employee and work date never change: reserve is a no-op on recalculations.
            if isinstance(event, DailyTimeResultCalculated | DailyTimeResultImported):
                await self._store.reserve(
                    EMPLOYEE_WORK_DATE_SCOPE, _employee_work_date_key(event.employee_id, event.work_date), stream_id
                )
        await self._store.append(
            stream_type=DAILY_TIME_RESULT_STREAM,
            stream_id=stream_id,
            expected_version=daily_time_result.version,
            events=events,
        )
        daily_time_result._advance_version(len(events))

    async def delete(self, daily_time_result_id: DailyTimeResultId) -> None:
        raise NotImplementedError("Event-sourced daily time results are never deleted")

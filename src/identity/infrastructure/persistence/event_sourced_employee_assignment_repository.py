"""Event-store adapter for the EmployeeAssignment aggregate (write side)."""

from datetime import date

from core.domain.errors import NotFoundError
from core.infrastructure.event_store import EventStore

from ...domain.entities import EmployeeAssignment
from ...domain.events import (
    EmployeeAssigned,
    EmployeeAssignmentCancelled,
    EmployeeAssignmentEnded,
    EmployeeAssignmentImported,
)
from ...domain.repositories import IEmployeeAssignmentRepository
from ...domain.value_objects.ids import EmployeeAssignmentId, EmployeeId

EMPLOYEE_ASSIGNMENT_STREAM = "identity.employee_assignment"

EMPLOYEE_ASSIGNMENT_EVENT_TYPES = {
    "users.employee_assignment.created": EmployeeAssigned,
    "users.employee_assignment.ended": EmployeeAssignmentEnded,
    "users.employee_assignment.imported": EmployeeAssignmentImported,
    "users.employee_assignment.cancelled": EmployeeAssignmentCancelled,
}


def _overlaps(assignment: EmployeeAssignment, start_date: date, end_date: date | None) -> bool:
    """``[start_date, end_date]`` intersects the assignment (open end = forever)."""
    return assignment.start_date <= (end_date or date.max) and (
        assignment.end_date is None or assignment.end_date >= start_date
    )


class EventSourcedEmployeeAssignmentRepository(IEmployeeAssignmentRepository):
    """An assignment is the replay of its stream; an employee has few, so the
    lookups load all of the employee's assignments and filter them."""

    def __init__(self, event_store: EventStore) -> None:
        self._store = event_store

    async def get_by_id(self, employee_assignment_id: EmployeeAssignmentId) -> EmployeeAssignment:
        events = await self._store.load(employee_assignment_id.value, EMPLOYEE_ASSIGNMENT_EVENT_TYPES)
        if not events:
            raise NotFoundError(
                f"EmployeeAssignment {employee_assignment_id} not found", context=employee_assignment_id.value
            )
        return EmployeeAssignment.rehydrate(employee_assignment_id, events)

    async def exists(self, employee_assignment_id: EmployeeAssignmentId) -> bool:
        return await self._store.exists(employee_assignment_id.value, EMPLOYEE_ASSIGNMENT_STREAM)

    async def exists_overlapping(
        self,
        employee_id: EmployeeId,
        start_date: date,
        end_date: date | None,
        *,
        excluding: EmployeeAssignmentId | None = None,
    ) -> bool:
        return any(
            _overlaps(assignment, start_date, end_date) and assignment.id != excluding
            for assignment in await self.find_by_employee(employee_id)
        )

    async def find_active(self, employee_id: EmployeeId, day: date) -> EmployeeAssignment | None:
        return next(
            (assignment for assignment in await self.find_by_employee(employee_id) if assignment.is_active_on(day)),
            None,
        )

    async def find_by_employee(self, employee_id: EmployeeId) -> list[EmployeeAssignment]:
        """The employee's assignments, most recent start first (cancelled ones left out)."""
        ids = await self._store.find_stream_ids(EMPLOYEE_ASSIGNMENT_STREAM, {"employee_id": employee_id.value})
        streams = await self._store.load_streams(ids, EMPLOYEE_ASSIGNMENT_EVENT_TYPES)
        assignments = [
            EmployeeAssignment.rehydrate(EmployeeAssignmentId(stream_id), events) for stream_id, events in streams.items()
        ]
        assignments = [assignment for assignment in assignments if not assignment.is_cancelled]
        return sorted(assignments, key=lambda assignment: assignment.start_date, reverse=True)

    async def save(self, employee_assignment: EmployeeAssignment) -> None:
        events = employee_assignment.domain_events
        await self._store.append(
            stream_type=EMPLOYEE_ASSIGNMENT_STREAM,
            stream_id=employee_assignment.id.value,
            expected_version=employee_assignment.version,
            events=events,
        )
        employee_assignment._advance_version(len(events))

    async def delete(self, employee_assignment_id: EmployeeAssignmentId) -> None:
        raise NotImplementedError("Event-sourced employee assignments are never deleted")

"""Event-store adapter for the Employee aggregate (write side)."""

from core.domain.errors import NotFoundError
from core.infrastructure.event_store import EventStore
from identity.domain.repositories.employee_repository import IEmployeeWriteRepository

from ...domain.entities import Employee
from ...domain.events import (
    EmployeeActivated,
    EmployeeCompanySet,
    EmployeeCreated,
    EmployeeDeactivated,
    EmployeeImported,
    EmployeeRoleChanged,
    EmployeeUpdated,
)
from ...domain.value_objects.ids import EmployeeId, UserId

EMPLOYEE_STREAM = "identity.employee"

EMPLOYEE_EVENT_TYPES = {
    "users.employee.created": EmployeeCreated,
    "users.employee.updated": EmployeeUpdated,
    "users.employee.imported": EmployeeImported,
    "users.employee.role_changed": EmployeeRoleChanged,
    "users.employee.deactivated": EmployeeDeactivated,
    "users.employee.activated": EmployeeActivated,
    "users.employee.company_set": EmployeeCompanySet,
}

EMPLOYEE_NUMBER_KEY = "identity.employee.employee_number"


class EventSourcedEmployeeRepository(IEmployeeWriteRepository):
    """An employee is the replay of its stream; the employee number is a unique key."""

    def __init__(self, event_store: EventStore) -> None:
        self._store = event_store

    async def get_by_id(self, employee_id: EmployeeId) -> Employee:
        events = await self._store.load(employee_id.value, EMPLOYEE_EVENT_TYPES)
        if not events:
            raise NotFoundError(f"Employee {employee_id} not found", context=employee_id.value)
        return Employee.rehydrate(employee_id, events)

    async def exists(self, employee_id: EmployeeId) -> bool:
        return await self._store.exists(employee_id.value, EMPLOYEE_STREAM)

    async def exists_by_employee_number(self, employee_number: str) -> bool:
        return await self._store.owner(EMPLOYEE_NUMBER_KEY, employee_number) is not None

    async def find_by_user_id(self, user_id: UserId) -> Employee | None:
        # employees.user_id is not unique: prefer the active, most recent record.
        ids = await self._store.find_stream_ids(EMPLOYEE_STREAM, {"user_id": user_id.value})
        streams = await self._store.load_streams(ids, EMPLOYEE_EVENT_TYPES)
        employees = [Employee.rehydrate(EmployeeId(stream_id), events) for stream_id, events in streams.items()]
        if not employees:
            return None
        return max(employees, key=lambda employee: (employee.is_active, employee.created_at))

    async def find_by_employee_number(self, employee_number: str) -> Employee | None:
        """The employee whose *current* number is ``employee_number`` (the active one first)."""
        ids = await self._store.find_stream_ids(EMPLOYEE_STREAM, {"employee_number": employee_number})
        streams = await self._store.load_streams(ids, EMPLOYEE_EVENT_TYPES)
        employees = [
            employee
            for stream_id, events in streams.items()
            if (employee := Employee.rehydrate(EmployeeId(stream_id), events)).employee_number == employee_number
        ]
        if not employees:
            return None
        return max(employees, key=lambda employee: (employee.is_active, employee.created_at))

    async def save(self, employee: Employee) -> None:
        events = employee.domain_events
        number = None
        for event in events:
            if isinstance(event, EmployeeCreated | EmployeeImported | EmployeeUpdated):
                number = event.employee_number
        if number is not None:
            previous = None
            if employee.version > 0:
                previous = (await self.get_by_id(employee.id)).employee_number
            if previous is not None and previous != number:
                await self._store.release(EMPLOYEE_NUMBER_KEY, previous, employee.id.value)
            await self._store.reserve(EMPLOYEE_NUMBER_KEY, number, employee.id.value)
        await self._store.append(
            stream_type=EMPLOYEE_STREAM,
            stream_id=employee.id.value,
            expected_version=employee.version,
            events=events,
        )
        employee._advance_version(len(events))

    async def delete(self, employee_id: EmployeeId) -> None:
        raise NotImplementedError("Event-sourced employees are never deleted")

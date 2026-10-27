"""EventSourcedEmployeeRepository.find_by_employee_number matches the *current* number."""

import asyncio

from identity.domain import EmployeeId, UserId
from identity.domain.entities import Employee
from identity.infrastructure.persistence.event_sourced_employee_repository import (
    EMPLOYEE_STREAM,
    EventSourcedEmployeeRepository,
)


class FakeEventStore:
    """Streams of employee events; payload containment like the JSONB ``@>`` lookup."""

    def __init__(self, *employees):
        self.streams = {e.id.value: list(e.domain_events) for e in employees}

    async def find_stream_ids(self, stream_type, contains=None):
        assert stream_type == EMPLOYEE_STREAM
        return [
            stream_id
            for stream_id, events in self.streams.items()
            if any(contains.items() <= event.to_payload().items() for event in events)
        ]

    async def load_streams(self, stream_ids, event_types):
        return {stream_id: self.streams[stream_id] for stream_id in stream_ids}


def employee(n, number, *, is_active=True):
    return Employee.create(EmployeeId(f"emp{n}"), user_id=UserId(f"usr{n}"), employee_number=number, is_active=is_active)


def test_finds_by_current_number_only_and_prefers_the_active_record():
    renumbered = employee(1, "EMP0000001")
    renumbered.update(employee_number="EMP0000009", is_active=None, phone=None)
    old_record = employee(2, "EMP0000002", is_active=False)
    current = employee(3, "EMP0000002")
    repo = EventSourcedEmployeeRepository(FakeEventStore(renumbered, old_record, current))

    assert asyncio.run(repo.find_by_employee_number("EMP0000001")) is None  # its former number
    assert asyncio.run(repo.find_by_employee_number("EMP0000009")).id == EmployeeId("emp1")
    assert asyncio.run(repo.find_by_employee_number("EMP0000002")).id == EmployeeId("emp3")
    assert asyncio.run(repo.find_by_employee_number("EMP0000404")) is None

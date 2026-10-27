"""Shared fixtures for the adjustements tests: event-stream fakes of the write
repositories, an in-memory read side computed from them, an in-memory selfie
storage, a fake time-calculation container, and a TestClient over the real
anomalies router and the real ``AdjustementsContainer`` wiring (pattern of
``tests/punch/conftest.py``).

No ``__init__.py`` here: it would shadow the ``adjustements`` source package.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from adjustements.application.dtos import AnomalyListItemDTO
from adjustements.domain.entities import Anomaly
from adjustements.domain.value_objects import AnomalyId, AnomalyStatus, AnomalyType, Severity
from adjustements.infrastructure.container import AdjustementsContainer
from adjustements.interface.dependancies import get_anomalies
from adjustements.interface.routers import anomalies_router
from auth.application.dtos import PrincipalDTO
from auth.interface import get_current_principal
from core.domain.errors import ConflictError, NotFoundError
from core.exceptions import register_exception_handlers
from identity.domain import EmployeeId, Role, UserId
from identity.domain.entities import Employee, User
from identity.domain.value_objects.location import Location
from punch.domain import EntrySource, EntryType, LocationConfidence, TimeEntryId, TimeEntryValidationStatus
from punch.domain.entities import TimeEntry
from time_calculation.interface import get_time_calculation

COTONOU = Location(6.3654, 2.4183)
JPEG = b"\xff\xd8\xff\xe0fake-jpeg"


class InMemoryPhotoStorage:
    """Test double for ``IPhotoStorage``: a dict key -> (content, content_type)."""

    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    async def put(self, key: str, content: bytes, content_type: str) -> None:
        self.objects[key] = (content, content_type)

    async def get(self, key: str) -> tuple[bytes, str]:
        try:
            return self.objects[key]
        except KeyError:
            raise NotFoundError(f"Photo {key!r} not found", context=key) from None


class InMemoryStreams:
    """An event-sourced repository double: one event list per aggregate,
    optimistic concurrency on the version, rehydration on every load."""

    def __init__(self, aggregate_type) -> None:
        self._type = aggregate_type
        self.streams: dict[str, list] = {}
        self._ids: dict[str, object] = {}

    async def get_by_id(self, aggregate_id):
        events = self.streams.get(aggregate_id.value)
        if not events:
            raise NotFoundError(f"{self._type.__name__} {aggregate_id} not found", context=aggregate_id.value)
        return self._type.rehydrate(aggregate_id, events)

    async def save(self, aggregate) -> None:
        stream = self.streams.setdefault(aggregate.id.value, [])
        if len(stream) != aggregate.version:
            raise ConflictError(f"Stream {aggregate.id.value} moved on", context=aggregate.id.value)
        events = aggregate.domain_events
        stream.extend(events)
        self._ids[aggregate.id.value] = aggregate.id
        aggregate._advance_version(len(events))

    def current(self, id_value: str):
        return self._type.rehydrate(self._ids[id_value], self.streams[id_value])

    def all(self) -> list:
        return [self.current(id_value) for id_value in self.streams]


class InMemoryEmployees:
    def __init__(self) -> None:
        self.items: list[Employee] = []

    async def find_by_user_id(self, user_id):
        return next((e for e in self.items if e.user_id == user_id), None)


class InMemoryAnomalyReadRepository:
    """The read-side join, computed from the in-memory write side (what the
    SQL of ``AnomalyReadRepository`` does against the read database)."""

    def __init__(self, ns) -> None:
        self._ns = ns

    def _items(self, status=None, type=None) -> list[AnomalyListItemDTO]:
        users = {u.id.value: u for u in self._ns.users}
        employees = {e.id.value: e for e in self._ns.employees.items}
        items = []
        for anomaly in self._ns.anomalies.all():
            if status is not None and anomaly.status != status:
                continue
            if type is not None and anomaly.type != type:
                continue
            entry = self._ns.time_entries.current(anomaly.time_entry_id.value)
            employee = employees.get((anomaly.employee_id or entry.employee_id).value)
            punched = users.get(employee.user_id.value) if employee else None
            assistant = users.get(anomaly.assisted_by_user_id.value) if anomaly.assisted_by_user_id else None
            items.append(
                AnomalyListItemDTO(
                    id=anomaly.id.value,
                    type=anomaly.type,
                    severity=anomaly.severity,
                    status=anomaly.status,
                    detected_at=anomaly.detected_at,
                    employee_id=employee.id.value if employee else None,
                    employee_number=employee.employee_number if employee else None,
                    employee_first_name=punched.first_name if punched else None,
                    employee_last_name=punched.last_name if punched else None,
                    assisted_by_first_name=assistant.first_name if assistant else None,
                    assisted_by_last_name=assistant.last_name if assistant else None,
                    occured_at=entry.occured_at,
                    entry_type=entry.entry_type,
                    photo_key=entry.photo_key,
                    decided_at=anomaly.decided_at,
                    decision_comment=anomaly.decision_comment,
                )
            )
        return sorted(items, key=lambda i: i.detected_at, reverse=True)

    async def find(self, *, status=None, type=None, limit=20, offset=0):
        return self._items(status, type)[offset : offset + limit]

    async def count(self, *, status=None, type=None):
        return len(self._items(status, type))

    async def get(self, anomaly_id: str):
        return next((i for i in self._items() if i.id == anomaly_id), None)


class FakeTimeCalculation:
    """Records the recalculations; raises ``error`` when one is set."""

    def __init__(self) -> None:
        self.sent: list = []
        self.error: Exception | None = None

    async def send(self, request):
        self.sent.append(request)
        if self.error is not None:
            raise self.error
        return None


class _NoopUnitOfWork:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return None

    async def commit(self):
        pass

    async def rollback(self):
        pass


class _NullEventBus:
    def publish(self, event):
        pass


@pytest.fixture
def anomalies_api():
    """Real router + real AdjustementsContainer, every port faked.

    Seeds ``emp1`` / ``usr1`` (Marie Agossou, the assistant), ``emp2`` / ``usr2``
    (Paul Houngbo, the punched employee), ``emp3`` / ``usr3`` (Awa Dossou,
    MANAGER, the caller by default) and ``usr9`` (an ADMIN with no employee)."""
    ns = SimpleNamespace(
        employees=InMemoryEmployees(),
        users=[],
        anomalies=InMemoryStreams(Anomaly),
        time_entries=InMemoryStreams(TimeEntry),
        photos=InMemoryPhotoStorage(),
        time_calculation=FakeTimeCalculation(),
    )
    ns.read = InMemoryAnomalyReadRepository(ns)

    def add_person(n, *, first_name, last_name, role=Role.EMPLOYEE, employee=True):
        ns.users.append(
            User(
                UserId(f"usr{n}"),
                email=f"user{n}@pointage.bj",
                password_hash=None,
                role=role,
                first_name=first_name,
                last_name=last_name,
                is_active=True,
            )
        )
        if employee:
            ns.employees.items.append(
                Employee(
                    EmployeeId(f"emp{n}"),
                    user_id=UserId(f"usr{n}"),
                    employee_number=f"EMP{n:07d}",
                    is_active=True,
                    role=role,
                )
            )

    def _seed(aggregate, repository):
        asyncio.run(repository.save(aggregate))
        aggregate.collect_events()

    def add_assisted_punch(*, employee="emp2", assistant="usr1", photo=True, detected_at=None):
        """A PENDING assisted entry and its OPEN ASSISTED_POINTING anomaly."""
        entry_id = TimeEntryId.generate()
        photo_key = f"time-entries/{entry_id.value}.jpg" if photo else None
        entry = TimeEntry.create(
            entry_id,
            employee_id=EmployeeId(employee),
            entry_type=EntryType.IN,
            location=COTONOU,
            source=EntrySource.ASSISTED,
            idempotency_key=f"key-{entry_id.value}",
            assisted_by_user_id=UserId(assistant),
            photo_key=photo_key,
            validation_status=TimeEntryValidationStatus.PENDING,
        )
        anomaly = Anomaly.create(
            AnomalyId.generate(),
            time_entry_id=entry_id,
            type=AnomalyType.ASSISTED_POINTING,
            severity=Severity.BLOCKING,
            status=AnomalyStatus.OPEN,
            detected_at=detected_at or datetime.now(UTC),
            description=f"Pointage assisté depuis le compte {assistant}",
            employee_id=EmployeeId(employee),
            assisted_by_user_id=UserId(assistant),
        )
        _seed(entry, ns.time_entries)
        _seed(anomaly, ns.anomalies)
        if photo:
            ns.photos.objects[photo_key] = (JPEG, "image/jpeg")
        return anomaly.id.value

    def add_late_anomaly(*, employee="emp2"):
        """An older LATE anomaly on an ordinary COUNTED entry, no photo, no assistant."""
        entry_id = TimeEntryId.generate()
        entry = TimeEntry.create(
            entry_id,
            employee_id=EmployeeId(employee),
            entry_type=EntryType.IN,
            location=COTONOU,
            location_confidence=LocationConfidence.HIGH,
            idempotency_key=f"key-{entry_id.value}",
        )
        anomaly = Anomaly.create(
            AnomalyId.generate(),
            time_entry_id=entry_id,
            type=AnomalyType.LATE,
            severity=Severity.WARNING,
            status=AnomalyStatus.OPEN,
            detected_at=datetime.now(UTC) - timedelta(days=1),
        )
        _seed(entry, ns.time_entries)
        _seed(anomaly, ns.anomalies)
        return anomaly.id.value

    container = AdjustementsContainer(
        anomaly_repository=ns.anomalies,
        time_entry_repository=ns.time_entries,
        employee_repository=ns.employees,
        anomaly_read_repository=ns.read,
        photo_storage=ns.photos,
        unit_of_work=_NoopUnitOfWork(),
        event_bus=_NullEventBus(),
    )
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(anomalies_router)
    app.dependency_overrides[get_anomalies] = lambda: container
    app.dependency_overrides[get_time_calculation] = lambda: ns.time_calculation

    def act_as(user_id, role="MANAGER"):
        app.dependency_overrides[get_current_principal] = lambda: PrincipalDTO(user_id=user_id, role=role)

    ns.container = container
    ns.act_as = act_as
    ns.add_assisted_punch = add_assisted_punch
    ns.add_late_anomaly = add_late_anomaly
    ns.client = TestClient(app)
    add_person(1, first_name="Marie", last_name="Agossou")
    add_person(2, first_name="Paul", last_name="Houngbo")
    add_person(3, first_name="Awa", last_name="Dossou", role=Role.MANAGER)
    add_person(9, first_name="Admin", last_name="Root", role=Role.ADMIN, employee=False)
    act_as("usr3")
    return ns

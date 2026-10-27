"""Shared fixtures for the punch tests: an in-memory selfie storage, in-memory
write repositories, and a TestClient over the real time-entries router and
the real ``PunchesContainer`` wiring (pattern of ``tests/identity/conftest.py``)."""

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from auth.application.dtos import PrincipalDTO
from auth.interface import get_current_principal
from core.domain.errors import ConflictError, NotFoundError
from core.exceptions import register_exception_handlers
from identity.domain import DirectoryId, EmployeeId, Role, SiteId, SiteKind, UserId
from identity.domain.entities import Employee, Site, User
from identity.domain.value_objects.location import Location
from punch.domain import TimeEntryValidationStatus
from punch.infrastructure import PunchesContainer
from punch.interface import get_punches
from punch.interface.routers import manager_time_entries_router, time_entries_router

COTONOU = Location(6.3654, 2.4183)
PORTO_NOVO = Location(6.4969, 2.6289)


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


@pytest.fixture
def photo_storage() -> InMemoryPhotoStorage:
    return InMemoryPhotoStorage()


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


class InMemoryEmployees:
    def __init__(self) -> None:
        self.items: list[Employee] = []

    async def get_by_id(self, employee_id):
        for employee in self.items:
            if employee.id == employee_id:
                return employee
        raise NotFoundError(f"Employee {employee_id} not found", context=employee_id.value)

    async def find_by_employee_number(self, employee_number):
        return next((e for e in self.items if e.employee_number == employee_number), None)

    async def find_by_user_id(self, user_id):
        return next((e for e in self.items if e.user_id == user_id), None)


class InMemoryUsers:
    def __init__(self) -> None:
        self.items: list[User] = []

    async def get_by_id(self, user_id):
        for user in self.items:
            if user.id == user_id:
                return user
        raise NotFoundError(f"User {user_id} not found", context=user_id.value)


class InMemorySites:
    def __init__(self) -> None:
        self.items: list[Site] = []

    async def get_by_id(self, site_id):
        for site in self.items:
            if site.id == site_id:
                return site
        raise NotFoundError(f"Site {site_id} not found", context=site_id.value)


class InMemoryAssignments:
    """employee_id -> assignment (active every day)."""

    def __init__(self) -> None:
        self.by_employee: dict[EmployeeId, SimpleNamespace] = {}

    async def find_active(self, employee_id, day):
        return self.by_employee.get(employee_id)


class InMemoryTimeEntries:
    """Saved entries plus the ``punch.idempotency_key`` unique keys, like the event store."""

    def __init__(self) -> None:
        self.items: list = []
        self.idempotency_keys: dict[str, str] = {}

    async def save(self, time_entry):
        self.items.append(time_entry)

    async def find_last_by_employee_id(self, employee_id):
        entries = [
            e
            for e in self.items
            if e.employee_id == employee_id and e.validation_status != TimeEntryValidationStatus.REJECTED
        ]
        return max(entries, key=lambda e: e.occured_at, default=None)

    async def reserve_idempotency_key(self, idempotency_key, time_entry_id):
        holder = self.idempotency_keys.get(idempotency_key)
        if holder is not None and holder != time_entry_id.value:
            raise ConflictError(f"punch.idempotency_key {idempotency_key!r} is already taken", context=idempotency_key)
        self.idempotency_keys[idempotency_key] = time_entry_id.value


class InMemoryAnomalies:
    def __init__(self) -> None:
        self.items: list = []

    async def save(self, anomaly):
        self.items.append(anomaly)


@pytest.fixture
def punch_api(photo_storage):
    """Real router + real PunchesContainer (so a missing handler binding fails
    the test), with the repositories and the photo storage replaced by fakes.

    Seeds two employees: ``emp1`` / ``usr1`` (Marie, the caller by default, site
    at Cotonou) and ``emp2`` / ``usr2`` (Paul, site at Cotonou)."""
    ns = SimpleNamespace(
        employees=InMemoryEmployees(),
        users=InMemoryUsers(),
        sites=InMemorySites(),
        assignments=InMemoryAssignments(),
        time_entries=InMemoryTimeEntries(),
        anomalies=InMemoryAnomalies(),
        photos=photo_storage,
    )

    def add_employee(n, *, first_name, last_name, site_location=COTONOU, is_active=True, assigned=True):
        employee = Employee(
            EmployeeId(f"emp{n}"),
            user_id=UserId(f"usr{n}"),
            employee_number=f"EMP{n:07d}",
            is_active=is_active,
            role=Role.EMPLOYEE,
        )
        ns.employees.items.append(employee)
        ns.users.items.append(
            User(
                UserId(f"usr{n}"),
                email=f"user{n}@pointage.bj",
                password_hash=None,
                role=Role.EMPLOYEE,
                first_name=first_name,
                last_name=last_name,
                is_active=is_active,
            )
        )
        site = Site.create(
            SiteId.generate(), directory_id=DirectoryId(f"dir{n}"), name=f"Site {n}", location=site_location,
            kind=SiteKind.PRINCIPAL,
        )
        ns.sites.items.append(site)
        if assigned:
            ns.assignments.by_employee[employee.id] = SimpleNamespace(site_id=site.id, directory_id=site.directory_id)
        return employee

    container = PunchesContainer(
        time_entry_repository=ns.time_entries,
        employee_repository=ns.employees,
        site_repository=ns.sites,
        employee_assignment_repository=ns.assignments,
        user_repository=ns.users,
        anomaly_repository=ns.anomalies,
        photo_storage=photo_storage,
        unit_of_work=_NoopUnitOfWork(),
        event_bus=_NullEventBus(),
    )
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(time_entries_router)
    app.include_router(manager_time_entries_router)
    app.dependency_overrides[get_punches] = lambda: container

    def act_as(user_id, role="EMPLOYEE"):
        app.dependency_overrides[get_current_principal] = lambda: PrincipalDTO(user_id=user_id, role=role)

    ns.add_employee = add_employee
    ns.act_as = act_as
    ns.client = TestClient(app)
    add_employee(1, first_name="Marie", last_name="Agossou")
    add_employee(2, first_name="Paul", last_name="Houngbo")
    act_as("usr1")
    return ns

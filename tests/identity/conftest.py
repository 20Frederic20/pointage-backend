"""Shared fixtures for the identity tests: in-memory read side, factories,
and a TestClient over the real routers and the real UsersContainer wiring."""

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.domain.errors import NotFoundError
from core.exceptions import register_exception_handlers
from identity.domain import DirectoryId, EmployeeId, Role, UserId
from identity.domain.entities import Directory, Employee, User
from identity.infrastructure import UsersContainer
from identity.interface import get_users
from identity.interface.routers import directories_router, employees_router, users_router


class InMemoryReadRepository:
    """get_by_id / find / count over a list, filtering with the domain specs
    exactly like the SQL translator would (no spec = everything)."""

    def __init__(self, items, label):
        self.items = list(items)
        self._label = label

    async def get_by_id(self, entity_id):
        for item in self.items:
            if item.id == entity_id:
                return item
        raise NotFoundError(f"{self._label} {entity_id} not found", context=entity_id.value)

    async def find(self, spec=None, *, limit=50, offset=0):
        return self._matching(spec)[offset : offset + limit]

    async def count(self, spec=None):
        return len(self._matching(spec))

    def _matching(self, spec):
        return [item for item in self.items if spec is None or spec.is_satisfied_by(item)]


class _NullEventBus:
    def publish(self, event):
        pass


@pytest.fixture
def run():
    return asyncio.run


@pytest.fixture
def in_memory():
    return InMemoryReadRepository


@pytest.fixture
def make_employee():
    def make(n, *, role=Role.EMPLOYEE, is_active=True, phone="0102030405"):
        return Employee(
            EmployeeId(f"emp{n}"),
            user_id=UserId(f"usr{n}"),
            employee_number=f"EMP{n:07d}",
            is_active=is_active,
            phone=phone,
            role=role,
        )

    return make


@pytest.fixture
def make_user():
    def make(n, *, role=Role.EMPLOYEE, is_active=True, first_name="Ana", last_name="Dossou"):
        return User(
            UserId(f"usr{n}"),
            email=f"user{n}@pointage.bj",
            password_hash=None,
            role=role,
            first_name=first_name,
            last_name=last_name,
            is_active=is_active,
        )

    return make


@pytest.fixture
def make_directory():
    def make(n, *, name=None):
        return Directory(DirectoryId(f"dir{n}"), name=name or f"Direction {n}", code=f"D{n:03d}")

    return make


@pytest.fixture
def identity_api():
    """Real routers + real UsersContainer (so a missing handler binding fails
    the test), with only the read repositories replaced by in-memory fakes."""
    employees = InMemoryReadRepository([], "Employee")
    users = InMemoryReadRepository([], "User")
    directories = InMemoryReadRepository([], "Directory")
    container = UsersContainer(
        user_repository=None,
        directory_repository=None,
        employee_repository=None,
        site_repository=None,
        employee_assignment_repository=None,
        user_read_repository=users,
        directory_read_repository=directories,
        employee_read_repository=employees,
        site_read_repository=None,
        employee_assignment_read_repository=None,
        unit_of_work=None,
        event_bus=_NullEventBus(),
        password_hasher=None,
    )
    app = FastAPI()
    register_exception_handlers(app)
    for router in (employees_router, users_router, directories_router):
        app.include_router(router)
    app.dependency_overrides[get_users] = lambda: container
    return SimpleNamespace(client=TestClient(app), employees=employees, users=users, directories=directories)


# ---- In-memory WRITE side, for command-handler tests -----------------------


class NoopUnitOfWork:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class InMemoryWriteRepository:
    """get_by_id / exists / save keyed by id; saved aggregates have their events drained."""

    def __init__(self, label):
        self.items = {}
        self._label = label

    def add(self, *aggregates):
        for aggregate in aggregates:
            aggregate.collect_events()
            self.items[aggregate.id] = aggregate
        return aggregates[0] if len(aggregates) == 1 else aggregates

    async def get_by_id(self, aggregate_id):
        if aggregate_id not in self.items:
            raise NotFoundError(f"{self._label} {aggregate_id} not found", context=aggregate_id.value)
        return self.items[aggregate_id]

    async def exists(self, aggregate_id):
        return aggregate_id in self.items

    async def save(self, aggregate):
        self.items[aggregate.id] = aggregate


class InMemoryEmployees(InMemoryWriteRepository):
    def __init__(self):
        super().__init__("Employee")

    async def find_all_by_user_id(self, user_id):
        return [e for e in self.items.values() if e.user_id == user_id]

    async def find_by_user_id(self, user_id):
        matches = await self.find_all_by_user_id(user_id)
        return max(matches, key=lambda e: e.is_active, default=None)

    async def exists_by_employee_number(self, number):
        return any(e.employee_number == number for e in self.items.values())

    async def find_by_employee_number(self, number):
        return next((e for e in self.items.values() if e.employee_number == number), None)


class InMemoryAssignments(InMemoryWriteRepository):
    def __init__(self):
        super().__init__("EmployeeAssignment")

    async def find_by_employee(self, employee_id):
        found = [a for a in self.items.values() if a.employee_id == employee_id and not a.is_cancelled]
        return sorted(found, key=lambda a: a.start_date, reverse=True)

    async def find_active(self, employee_id, day):
        return next((a for a in await self.find_by_employee(employee_id) if a.is_active_on(day)), None)

    async def exists_overlapping(self, employee_id, start_date, end_date, *, excluding=None):
        from datetime import date as _date

        return any(
            a.id != excluding and a.start_date <= (end_date or _date.max) and (a.end_date is None or a.end_date >= start_date)
            for a in await self.find_by_employee(employee_id)
        )


class InMemorySites(InMemoryWriteRepository):
    def __init__(self):
        super().__init__("Site")

    async def find_principal(self, directory_id):
        return next((s for s in self.items.values() if s.directory_id == directory_id and s.is_principal()), None)


@pytest.fixture
def write_side():
    """Users, employees, directories, sites and assignments in memory, plus a company R
    (root dir1) with a department dir2 and its principal site, and an outside company dir9."""
    from identity.domain import SiteId, SiteKind
    from identity.domain.entities import Site
    from identity.domain.value_objects.location import Location

    side = SimpleNamespace(
        unit_of_work=NoopUnitOfWork(),
        users=InMemoryWriteRepository("User"),
        employees=InMemoryEmployees(),
        directories=InMemoryWriteRepository("Directory"),
        sites=InMemorySites(),
        assignments=InMemoryAssignments(),
    )
    side.directories.add(
        Directory(DirectoryId("dir1"), name="Société R", code="R", parent_directory_id=None),
        Directory(DirectoryId("dir2"), name="Agence Nord", code="RN", parent_directory_id=DirectoryId("dir1")),
        Directory(DirectoryId("dir9"), name="Autre société", code="X", parent_directory_id=None),
    )
    for n, directory in ((1, "dir1"), (2, "dir2"), (9, "dir9")):
        side.sites.add(Site(SiteId(f"site{n}"), directory_id=DirectoryId(directory), name=f"Site {n}",
                            location=Location(6.4, 2.6), kind=SiteKind.PRINCIPAL))
    return side


@pytest.fixture
def identity_write_api(write_side):
    """Real routers + real UsersContainer over the in-memory write side (write and read
    repositories are the same objects), and ``as_(role, user_id)`` to pick the caller."""
    from auth.application.dtos import PrincipalDTO
    from auth.interface import get_current_principal
    from identity.interface.routers import employee_assignments_router

    container = UsersContainer(
        user_repository=write_side.users,
        directory_repository=write_side.directories,
        employee_repository=write_side.employees,
        site_repository=write_side.sites,
        employee_assignment_repository=write_side.assignments,
        user_read_repository=write_side.users,
        directory_read_repository=write_side.directories,
        employee_read_repository=write_side.employees,
        site_read_repository=write_side.sites,
        employee_assignment_read_repository=write_side.assignments,
        unit_of_work=write_side.unit_of_work,
        event_bus=_NullEventBus(),
        password_hasher=None,
    )
    app = FastAPI()
    register_exception_handlers(app)
    for router in (employees_router, users_router, directories_router, employee_assignments_router):
        app.include_router(router)
    app.dependency_overrides[get_users] = lambda: container

    def as_(role, user_id="usr99"):
        app.dependency_overrides[get_current_principal] = lambda: PrincipalDTO(user_id=user_id, role=role)

    as_("HR")
    return SimpleNamespace(client=TestClient(app), side=write_side, as_=as_)

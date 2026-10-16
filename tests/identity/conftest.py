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

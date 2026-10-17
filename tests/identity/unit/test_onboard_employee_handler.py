"""Onboarding: the account, the employee and the first assignment in one
command — nothing is saved when any check fails."""

import asyncio
from datetime import date

import pytest

from core.domain.errors import NotFoundError
from identity.application.commands import OnboardEmployeeCommand
from identity.application.handlers import OnboardEmployeeHandler
from identity.domain import DirectoryId, Role, SiteId, SiteKind, UserId
from identity.domain.entities import Directory, Site, User
from identity.domain.errors import (
    DirectoryHasNoSiteError,
    EmailAlreadyRegisteredError,
    EmployeeWithThisNumberAlreadyExistsError,
)
from identity.domain.value_objects.location import Location


def run(coro):
    return asyncio.run(coro)


class NoopUnitOfWork:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return None


class FakeUsers:
    def __init__(self, *users):
        self.rows = {u.email: u for u in users}
        self.saved = []

    async def find_by_email(self, email):
        return self.rows.get(email.strip().lower())

    async def save(self, user):
        self.saved.append(user)


class FakeEmployees:
    def __init__(self, *numbers):
        self.numbers = set(numbers)
        self.saved = []

    async def exists_by_employee_number(self, number):
        return number in self.numbers

    async def save(self, employee):
        self.saved.append(employee)


class FakeAssignments:
    def __init__(self):
        self.saved = []

    async def save(self, assignment):
        self.saved.append(assignment)


class FakeDirectories:
    def __init__(self, *directories):
        self.rows = {d.id: d for d in directories}

    async def get_by_id(self, directory_id):
        if directory_id not in self.rows:
            raise NotFoundError("directory", context=directory_id.value)
        return self.rows[directory_id]


class FakeSites:
    def __init__(self, *sites):
        self.rows = {s.id: s for s in sites}

    async def get_by_id(self, site_id):
        return self.rows[site_id]

    async def find_principal(self, directory_id):
        return next((s for s in self.rows.values() if s.directory_id == directory_id and s.is_principal()), None)


class FakeHasher:
    def hash(self, password):
        return f"hashed:{password}"


DIRECTORY = Directory.create(DirectoryId.generate(), code="DG", name="Direction générale")
PRINCIPAL = Site.create(
    SiteId.generate(), directory_id=DIRECTORY.id, name="Siège", location=Location(6.3654, 2.4183),
    kind=SiteKind.PRINCIPAL,
)


def build(*, users=(), numbers=(), sites=(PRINCIPAL,)):
    repos = {
        "user_repository": FakeUsers(*users),
        "employee_repository": FakeEmployees(*numbers),
        "employee_assignment_repository": FakeAssignments(),
        "directory_repository": FakeDirectories(DIRECTORY),
        "site_repository": FakeSites(*sites),
    }
    handler = OnboardEmployeeHandler(unit_of_work=NoopUnitOfWork(), password_hasher=FakeHasher(), **repos)
    return handler, repos


def command(**overrides):
    values = {
        "email": "ana@pointage.bj",
        "first_name": "Ana",
        "last_name": "Dossou",
        "directory_id": DIRECTORY.id.value,
        "employee_number": "EMP0000001",
        "role": Role.MANAGER,
        "is_active": True,
        "assignment_start_date": date(2026, 10, 1),
    }
    return OnboardEmployeeCommand(**(values | overrides))


def saved(repos):
    return tuple(len(repos[name].saved) for name in ("user_repository", "employee_repository",
                                                     "employee_assignment_repository"))


def test_creates_the_account_the_employee_and_the_assignment_together():
    handler, repos = build()
    dto = run(handler.handle(command()))

    [user] = repos["user_repository"].saved
    [employee] = repos["employee_repository"].saved
    [assignment] = repos["employee_assignment_repository"].saved
    assert (user.email, user.first_name, user.last_name) == ("ana@pointage.bj", "Ana", "Dossou")
    assert user.password_hash is None  # no password: logs in with an emailed code
    assert employee.user_id == user.id
    assert (user.role, employee.role) == (Role.MANAGER, Role.MANAGER)
    assert (assignment.employee_id, assignment.site_id, assignment.start_date) == (
        employee.id, PRINCIPAL.id, date(2026, 10, 1)
    )
    assert (dto.id, dto.user_id, dto.employee_number) == (employee.id.value, user.id.value, "EMP0000001")


def test_hashes_the_password_when_one_is_given():
    handler, repos = build()
    run(handler.handle(command(password="s3cret-pass")))
    assert repos["user_repository"].saved[0].password_hash == "hashed:s3cret-pass"


def test_role_defaults_to_employee_for_both():
    handler, repos = build()
    run(handler.handle(command(role=None)))
    assert repos["user_repository"].saved[0].role == Role.EMPLOYEE
    assert repos["employee_repository"].saved[0].role == Role.EMPLOYEE


def test_taken_email_saves_nothing():
    taken = User.register_owner(UserId.generate(), email="ana@pointage.bj", password_hash=None, role=Role.HR)
    handler, repos = build(users=(taken,))
    with pytest.raises(EmailAlreadyRegisteredError):
        run(handler.handle(command(email=" Ana@Pointage.BJ ")))
    assert saved(repos) == (0, 0, 0)


def test_taken_employee_number_saves_nothing():
    handler, repos = build(numbers=("EMP0000001",))
    with pytest.raises(EmployeeWithThisNumberAlreadyExistsError):
        run(handler.handle(command()))
    assert saved(repos) == (0, 0, 0)


def test_directory_without_site_saves_nothing():
    handler, repos = build(sites=())
    with pytest.raises(DirectoryHasNoSiteError):
        run(handler.handle(command()))
    assert saved(repos) == (0, 0, 0)

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
    def __init__(self, *numbers, records=()):
        self.numbers = set(numbers)
        self.records = list(records)
        self.saved = []

    async def find_all_by_user_id(self, user_id):
        return [e for e in self.records if e.user_id == user_id]

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


DEPARTMENT = Directory(DirectoryId("dirdept"), name="Agence", code="AG", parent_directory_id=DIRECTORY.id)
DEPARTMENT_SITE = Site.create(
    SiteId.generate(), directory_id=DEPARTMENT.id, name="Agence", location=Location(6.3654, 2.4183),
    kind=SiteKind.PRINCIPAL,
)


def build(*, users=(), numbers=(), sites=(PRINCIPAL, DEPARTMENT_SITE), records=()):
    repos = {
        "user_repository": FakeUsers(*users),
        "employee_repository": FakeEmployees(*numbers, records=records),
        "employee_assignment_repository": FakeAssignments(),
        "directory_repository": FakeDirectories(DIRECTORY, DEPARTMENT),
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
        "actor_user_id": "usr_admin",
        "actor_role": "ADMIN",
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


def test_onboard_with_existing_email_reuses_account_and_creates_second_record():
    existing = User.register_owner(UserId.generate(), email="ana@pointage.bj", password_hash="h", role=Role.MANAGER,
                                   first_name="Ana", last_name="Dossou")
    handler, repos = build(users=(existing,))
    dto = run(handler.handle(command(email=" Ana@Pointage.BJ ", first_name="Ignored", employee_number="EMP0000002")))
    assert repos["user_repository"].saved == []  # the account is reused untouched
    [employee] = repos["employee_repository"].saved
    assert (employee.user_id, employee.employee_number, employee.company_directory_id) == (
        existing.id, "EMP0000002", DIRECTORY.id)
    assert (dto.account_reused, existing.first_name, existing.role) == (True, "Ana", Role.MANAGER)


def test_onboard_same_company_twice_is_409():
    from identity.domain import EmployeeId
    from identity.domain.entities import Employee
    from identity.domain.errors import AlreadyActiveInCompanyError

    existing = User.register_owner(UserId.generate(), email="ana@pointage.bj", password_hash=None, role=Role.HR)
    record = Employee(EmployeeId.generate(), user_id=existing.id, employee_number="EMP0000001", is_active=True,
                      company_directory_id=DIRECTORY.id)
    handler, repos = build(users=(existing,), records=(record,))
    with pytest.raises(AlreadyActiveInCompanyError):
        run(handler.handle(command(employee_number="EMP0000002", directory_id=DEPARTMENT.id.value)))
    assert saved(repos) == (0, 0, 0)


def test_onboard_defaults_to_active():
    handler, repos = build()
    run(handler.handle(command(is_active=None)))
    assert repos["employee_repository"].saved[0].is_active is True


def test_onboard_stores_company_root_for_subdirectory():
    handler, repos = build()
    dto = run(handler.handle(command(directory_id=DEPARTMENT.id.value)))
    assert repos["employee_repository"].saved[0].company_directory_id == DIRECTORY.id
    assert dto.account_reused is False


def test_manager_cannot_onboard_an_admin():
    from identity.domain.errors import RoleCeilingError

    handler, repos = build()
    with pytest.raises(RoleCeilingError):
        run(handler.handle(command(role=Role.ADMIN, actor_role="MANAGER")))
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


def test_onboarding_cannot_demote_an_account_without_records():
    from identity.domain.errors import RoleCeilingError

    founder = User.register_owner(UserId.generate(), email="ana@pointage.bj", password_hash=None, role=Role.ADMIN)
    handler, repos = build(users=(founder,))
    with pytest.raises(RoleCeilingError):
        run(handler.handle(command(role=Role.EMPLOYEE, employee_number="EMP0000002")))
    assert saved(repos) == (0, 0, 0)


def test_manager_cannot_add_a_record_to_a_higher_account():
    from identity.domain import EmployeeId
    from identity.domain.entities import Employee
    from identity.domain.errors import RoleCeilingError

    hr = User.register_owner(UserId.generate(), email="ana@pointage.bj", password_hash=None, role=Role.HR)
    record = Employee(EmployeeId.generate(), user_id=hr.id, employee_number="EMP0000001", is_active=True,
                      role=Role.HR, company_directory_id=DirectoryId("dirother"))
    handler, repos = build(users=(hr,), records=(record,))
    with pytest.raises(RoleCeilingError):
        run(handler.handle(command(role=Role.EMPLOYEE, employee_number="EMP0000002", actor_role="MANAGER")))

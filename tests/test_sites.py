"""Sites rules against in-memory fakes: principal / annex, which site an
assignment points at, and punching against the assignment's site.

Run from ``backend/``: ``uv run pytest``.
"""

import asyncio
from types import SimpleNamespace

import pytest

from core.domain.errors import NotFoundError
from identity.application.commands import CreateSiteCommand, MakeSitePrincipalCommand
from identity.application.handlers import CreateSiteHandler, MakeSitePrincipalHandler
from identity.application.services import AssignmentSiteService
from identity.domain import DirectoryId, EmployeeId, Role, SiteId, SiteKind, UserId
from identity.domain.entities import Directory, Employee, Site
from identity.domain.errors import (
    DirectoryHasNoSiteError,
    PrincipalSiteCannotBeDeactivatedError,
    SiteInactiveError,
    SiteNotInDirectoryError,
)
from identity.domain.value_objects.location import Location
from punch.application.commands import CreateTimeEntryCommand
from punch.application.handlers.create_time_entry_handler import CreateTimeEntryHandler
from punch.domain import EntrySource
from punch.domain.errors import TooFarFromWorkplaceError

COTONOU = Location(6.3654, 2.4183)
PORTO_NOVO = Location(6.4969, 2.6289)


def run(coro):
    return asyncio.run(coro)


class NoopUnitOfWork:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return None

    async def commit(self):
        pass

    async def rollback(self):
        pass


class FakeSites:
    def __init__(self, *sites):
        self.rows = {s.id: s for s in sites}
        self.saved = []

    async def get_by_id(self, site_id):
        if site_id not in self.rows:
            raise NotFoundError("site", context=site_id.value)
        return self.rows[site_id]

    async def find_principal(self, directory_id):
        return next(
            (s for s in self.rows.values() if s.directory_id == directory_id and s.is_principal()), None
        )

    async def save(self, site):
        self.saved.append((site.id, site.kind))
        self.rows[site.id] = site


class FakeDirectories:
    def __init__(self, *directories):
        self.rows = {d.id: d for d in directories}

    async def get_by_id(self, directory_id):
        return self.rows[directory_id]


def directory(code="DG"):
    return Directory.create(DirectoryId.generate(), code=code, name=code)


def site(d, kind=SiteKind.PRINCIPAL, location=COTONOU, name="Siège"):
    return Site.create(SiteId.generate(), directory_id=d.id, name=name, location=location, kind=kind)


# ---- principal / annex -------------------------------------------------------


def test_first_site_is_principal_the_next_ones_are_annexes():
    d = directory()
    sites = FakeSites()
    handler = CreateSiteHandler(
        unit_of_work=NoopUnitOfWork(), site_repository=sites, directory_repository=FakeDirectories(d)
    )
    first = run(handler.handle(CreateSiteCommand(directory_id=d.id.value, name="Siège", location=COTONOU)))
    second = run(handler.handle(CreateSiteCommand(directory_id=d.id.value, name="Annexe", location=PORTO_NOVO)))
    assert (first.kind, second.kind) == ("PRINCIPAL", "ANNEX")


def test_make_principal_swaps_and_saves_the_demotion_first():
    d = directory()
    principal, annex = site(d), site(d, SiteKind.ANNEX, PORTO_NOVO, "Annexe")
    sites = FakeSites(principal, annex)
    handler = MakeSitePrincipalHandler(unit_of_work=NoopUnitOfWork(), site_repository=sites)
    dto = run(handler.handle(MakeSitePrincipalCommand(site_id=annex.id.value)))
    assert dto.kind == "PRINCIPAL"
    assert sites.saved == [(principal.id, SiteKind.ANNEX), (annex.id, SiteKind.PRINCIPAL)]


def test_principal_site_cannot_be_deactivated_and_inactive_site_cannot_become_principal():
    d = directory()
    principal, annex = site(d), site(d, SiteKind.ANNEX)
    with pytest.raises(PrincipalSiteCannotBeDeactivatedError):
        principal.deactivate()
    annex.deactivate()
    with pytest.raises(PrincipalSiteCannotBeDeactivatedError):
        annex.make_principal()


# ---- which site an assignment points at ------------------------------------


def test_assignment_defaults_to_the_principal_site_and_checks_the_requested_one():
    d, other = directory("DG"), directory("DRH")
    principal, annex, foreign = site(d), site(d, SiteKind.ANNEX), site(other)
    service = AssignmentSiteService(site_repository=FakeSites(principal, annex, foreign))

    assert run(service.resolve(d, None)) is principal
    assert run(service.resolve(d, annex.id.value)) is annex
    with pytest.raises(SiteNotInDirectoryError):
        run(service.resolve(d, foreign.id.value))
    annex.deactivate()
    with pytest.raises(SiteInactiveError):
        run(service.resolve(d, annex.id.value))
    with pytest.raises(DirectoryHasNoSiteError):
        run(AssignmentSiteService(site_repository=FakeSites()).resolve(d, None))


# ---- punching against the assignment's site ---------------------------------


def punch_env(assigned_site):
    employee = Employee.create(
        EmployeeId.generate(), user_id=UserId.generate(), employee_number="0000000001", is_active=True,
        role=Role.EMPLOYEE,
    )
    assignment = SimpleNamespace(site_id=assigned_site.id, directory_id=assigned_site.directory_id)

    async def find_by_user_id(_):
        return employee

    async def find_active(*_):
        return assignment

    async def find_last_by_employee_id(_):
        return None

    async def save(_):
        pass

    return CreateTimeEntryHandler(
        unit_of_work=NoopUnitOfWork(),
        time_entry_repository=SimpleNamespace(find_last_by_employee_id=find_last_by_employee_id, save=save),
        employee_repository=SimpleNamespace(find_by_user_id=find_by_user_id),
        site_repository=FakeSites(assigned_site),
        employee_assignment_repository=SimpleNamespace(find_active=find_active),
    )


def punch_at(location):
    return CreateTimeEntryCommand(user_id="u1", location=location, source=EntrySource.MOBILE)


def test_punch_is_measured_against_the_annex_the_employee_is_assigned_to():
    d = directory()
    annex = site(d, SiteKind.ANNEX, PORTO_NOVO, "Annexe Porto-Novo")
    handler = punch_env(annex)
    assert run(handler.handle(punch_at(PORTO_NOVO))).entry_type == "IN"
    with pytest.raises(TooFarFromWorkplaceError):  # at the principal site, ~27 km away
        run(handler.handle(punch_at(COTONOU)))


def test_punch_on_a_deactivated_site_is_refused():
    d = directory()
    annex = site(d, SiteKind.ANNEX)
    annex.deactivate()
    with pytest.raises(SiteInactiveError):
        run(punch_env(annex).handle(punch_at(COTONOU)))

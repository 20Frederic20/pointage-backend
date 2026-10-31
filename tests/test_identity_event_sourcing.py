"""Identity aggregates rebuild from their stored events alone (no database)."""

import json
from datetime import UTC, date, datetime

from identity.application.notifications import USERS_EVENT_MAPPERS
from identity.domain import DirectoryId, EmployeeAssignmentId, EmployeeId, Role, SiteId, SiteKind, UserId
from identity.domain.entities import Directory, Employee, EmployeeAssignment, Site, User
from identity.domain.events import (
    DirectoryImported,
    EmployeeAssignmentImported,
    EmployeeImported,
    SiteImported,
    UserImported,
)
from identity.domain.value_objects.location import Location
from identity.infrastructure.persistence.event_sourced_directory_repository import DIRECTORY_EVENT_TYPES
from identity.infrastructure.persistence.event_sourced_employee_assignment_repository import (
    EMPLOYEE_ASSIGNMENT_EVENT_TYPES,
)
from identity.infrastructure.persistence.event_sourced_employee_repository import EMPLOYEE_EVENT_TYPES
from identity.infrastructure.persistence.event_sourced_site_repository import SITE_EVENT_TYPES
from identity.infrastructure.persistence.event_sourced_user_repository import USER_EVENT_TYPES

CREATED = datetime(2025, 1, 6, 8, tzinfo=UTC)


def _replay(aggregate, event_types):
    """Store/load simulation: JSON payload round-trip, original identity restored."""
    loaded = []
    for event in aggregate.domain_events:
        assert event_types[event.get_event_name()] is type(event)
        assert type(event) in USERS_EVENT_MAPPERS
        copy = type(event).from_payload(json.loads(json.dumps(event.to_payload())))
        copy.restore_identity(event.event_id, event.occurred_at)
        loaded.append(copy)
    aggregate._advance_version(len(loaded))
    return type(aggregate).rehydrate(aggregate.id, loaded)


def _state(aggregate, *fields):
    return tuple(getattr(aggregate, field) for field in (*fields, "id", "created_at", "updated_at", "version"))


def test_user_life_replays_to_the_same_state():
    user = User.register_owner(UserId.generate(), email=" Boss@Pointage.BJ ", password_hash="h", role=Role.ADMIN)
    user.change_role(Role.HR)
    user.change_role(Role.HR)  # no-op
    user.update_profile(first_name="Ada", avatar_url="https://a.bj/x.png")
    user.update_profile(first_name="Ada")  # no-op
    user.record_activity()
    user.clear_password()
    user.clear_password()  # no-op
    user.deactivate()
    user.deactivate()  # no-op
    assert len(user.domain_events) == 6
    fields = ("email", "password_hash", "role", "first_name", "last_name", "avatar_url", "is_active", "last_active_at")
    replayed = _replay(user, USER_EVENT_TYPES)
    assert _state(replayed, *fields) == _state(user, *fields)
    assert (replayed.email, replayed.role, replayed.is_active, replayed.version) == ("boss@pointage.bj", Role.HR, False, 6)


def test_directory_site_employee_assignment_replay():
    directory = Directory.create(DirectoryId.generate(), code="DG", name=" Direction ")
    directory.update(code="DG", name="Direction")  # no-op after strip
    directory.rename("Direction générale")
    assert len(directory.domain_events) == 2
    assert _state(_replay(directory, DIRECTORY_EVENT_TYPES), "code", "name", "parent_directory_id") == _state(
        directory, "code", "name", "parent_directory_id"
    )

    site = Site.create(SiteId.generate(), directory_id=directory.id, name="Annexe", location=Location(6.4969, 2.6289),
                       kind=SiteKind.ANNEX, address="Porto-Novo")
    site.deactivate()
    site.activate()
    site.make_principal()
    site.make_annex()
    fields = ("directory_id", "name", "location", "kind", "address", "active")
    assert _state(_replay(site, SITE_EVENT_TYPES), *fields) == _state(site, *fields)

    employee = Employee.create(EmployeeId.generate(), user_id=UserId.generate(), employee_number="0000000001",
                               is_active=False, phone="0102030405")
    employee.update(employee_number=None, is_active=None, phone=None)  # no-op
    employee.update(employee_number="0000000002", is_active=True, phone=None)
    assert len(employee.domain_events) == 2
    fields = ("user_id", "employee_number", "is_active", "role", "phone")
    assert _state(_replay(employee, EMPLOYEE_EVENT_TYPES), *fields) == _state(employee, *fields)

    assignment = EmployeeAssignment.assign(EmployeeAssignmentId.generate(), employee_id=employee.id,
                                           directory_id=directory.id, site_id=site.id, start_date=date(2026, 1, 1))
    assignment.end(date(2026, 6, 30))
    fields = ("employee_id", "directory_id", "site_id", "start_date", "end_date")
    assert _state(_replay(assignment, EMPLOYEE_ASSIGNMENT_EVENT_TYPES), *fields) == _state(assignment, *fields)


def test_imported_events_keep_the_full_state_and_the_original_dates():
    def imported(aggregate_type, aggregate_id, event, event_types):
        event.restore_identity(event.event_id, datetime(2026, 5, 1, tzinfo=UTC))
        aggregate = aggregate_type.rehydrate(aggregate_id, [])
        aggregate.apply(event)
        aggregate.record_event(event)
        return aggregate, _replay(aggregate, event_types)

    user_id = UserId.generate()
    user, replayed = imported(User, user_id, UserImported(
        user_id, email="a@pointage.bj", password_hash=None, role=Role.MANAGER, first_name="A", last_name="B",
        avatar_url=None, is_active=False, last_active_at=CREATED, created_at=CREATED), USER_EVENT_TYPES)
    assert (replayed.created_at, replayed.updated_at, replayed.is_active, replayed.role) == (
        CREATED, datetime(2026, 5, 1, tzinfo=UTC), False, Role.MANAGER)

    directory_id = DirectoryId.generate()
    _, directory = imported(Directory, directory_id, DirectoryImported(
        directory_id, code="DG", name="D", parent_directory_id=None, created_at=CREATED), DIRECTORY_EVENT_TYPES)
    site_id = SiteId.generate()
    _, site = imported(Site, site_id, SiteImported(
        site_id, directory_id=directory_id, name="S", location=Location(6.3, 2.4), kind=SiteKind.PRINCIPAL,
        address=None, active=True, created_at=CREATED), SITE_EVENT_TYPES)
    employee_id = EmployeeId.generate()
    _, employee = imported(Employee, employee_id, EmployeeImported(
        employee_id, user_id=user_id, employee_number="0000000009", is_active=True, phone=None, role=Role.EMPLOYEE,
        created_at=CREATED), EMPLOYEE_EVENT_TYPES)
    assignment_id = EmployeeAssignmentId.generate()
    _, assignment = imported(EmployeeAssignment, assignment_id, EmployeeAssignmentImported(
        assignment_id, employee_id=employee_id, directory_id=directory_id, site_id=site_id,
        start_date=date(2025, 1, 6), end_date=None, created_at=CREATED), EMPLOYEE_ASSIGNMENT_EVENT_TYPES)
    assert {directory.created_at, site.created_at, employee.created_at, assignment.created_at} == {CREATED}
    assert (site.kind, site.is_principal(), employee.employee_number) == (SiteKind.PRINCIPAL, True, "0000000009")


def test_every_identity_event_has_a_type_and_a_mapper():
    every = {**USER_EVENT_TYPES, **DIRECTORY_EVENT_TYPES, **SITE_EVENT_TYPES, **EMPLOYEE_EVENT_TYPES,
             **EMPLOYEE_ASSIGNMENT_EVENT_TYPES}
    assert set(every.values()) == set(USERS_EVENT_MAPPERS)


def test_employee_role_change_activation_and_company_replay():
    employee = Employee.create(EmployeeId.generate(), user_id=UserId.generate(), employee_number="0000000003",
                               is_active=True, company_directory_id=DirectoryId("dir1"))
    employee.change_role(Role.HR)
    employee.deactivate()
    employee.activate()
    employee.set_company(DirectoryId("dir2"))
    assert len(employee.domain_events) == 5
    fields = ("user_id", "employee_number", "is_active", "role", "phone", "company_directory_id")
    replayed = _replay(employee, EMPLOYEE_EVENT_TYPES)
    assert _state(replayed, *fields) == _state(employee, *fields)
    assert (replayed.role, replayed.is_active, replayed.company_directory_id) == (Role.HR, True, DirectoryId("dir2"))


def test_deactivate_twice_or_activate_active_is_conflict():
    import pytest

    from identity.domain.errors import EmployeeAlreadyActiveError, EmployeeAlreadyInactiveError

    employee = Employee.create(EmployeeId.generate(), user_id=UserId.generate(), employee_number="0000000004",
                               is_active=True)
    with pytest.raises(EmployeeAlreadyActiveError):
        employee.activate()
    employee.deactivate()
    with pytest.raises(EmployeeAlreadyInactiveError):
        employee.deactivate()
    assert (EmployeeAlreadyActiveError.code, EmployeeAlreadyInactiveError.code) == (
        "EMPLOYEE_ALREADY_ACTIVE", "EMPLOYEE_ALREADY_INACTIVE")
    assert EmployeeAlreadyActiveError.http_status == EmployeeAlreadyInactiveError.http_status == 409


def test_change_role_to_same_role_records_nothing():
    employee = Employee.create(EmployeeId.generate(), user_id=UserId.generate(), employee_number="0000000005",
                               is_active=True, role=Role.MANAGER)
    employee.change_role(Role.MANAGER)
    employee.change_phone(None)
    assert len(employee.domain_events) == 1


def test_change_phone_updates_the_phone():
    employee = Employee.create(EmployeeId.generate(), user_id=UserId.generate(), employee_number="0000000006",
                               is_active=True)
    employee.change_phone("0197000000")
    assert _replay(employee, EMPLOYEE_EVENT_TYPES).phone == "0197000000"


def test_legacy_employee_created_payload_has_no_company():
    from identity.domain.events import EmployeeCreated

    employee = Employee.create(EmployeeId.generate(), user_id=UserId.generate(), employee_number="0000000007",
                               is_active=True, company_directory_id=DirectoryId("dir1"))
    payload = employee.domain_events[0].to_payload()
    del payload["company_directory_id"]
    legacy = Employee.rehydrate(employee.id, [EmployeeCreated.from_payload(payload)])
    assert legacy.company_directory_id is None

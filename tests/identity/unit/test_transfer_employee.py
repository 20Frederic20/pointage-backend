"""Transfers: assigning an employee ends or cancels the current assignment."""

from datetime import date

import pytest

from identity.application.commands import AssignEmployeeCommand
from identity.application.handlers import AssignEmployeeHandler
from identity.domain import DirectoryId, EmployeeAssignmentId, EmployeeId, Role, SiteId, UserId
from identity.domain.entities import Employee, EmployeeAssignment
from identity.domain.errors import (
    AssignmentInPastError,
    DirectoryOutsideCompanyError,
    EmployeeInactiveError,
    FutureAssignmentExistsError,
    RoleCeilingError,
)

TODAY = date(2026, 10, 31)


def _employee(side, *, role=Role.EMPLOYEE, active=True):
    return side.employees.add(Employee(EmployeeId("emp1"), user_id=UserId("usr1"), employee_number="EMP0000001",
                                       is_active=active, role=role, company_directory_id=DirectoryId("dir1")))


def _assignment(side, n, start, end=None, site="site1", directory="dir1"):
    return side.assignments.add(EmployeeAssignment(EmployeeAssignmentId(f"asg{n}"), employee_id=EmployeeId("emp1"),
                                                   directory_id=DirectoryId(directory), site_id=SiteId(site),
                                                   start_date=start, end_date=end))


def _assign(side, start, *, directory="dir2", site="site2", actor_role=Role.HR, end=None):
    handler = AssignEmployeeHandler(
        unit_of_work=side.unit_of_work,
        employee_assignment_repository=side.assignments,
        employee_repository=side.employees,
        directory_repository=side.directories,
        site_repository=side.sites,
        clock=lambda: TODAY,
    )
    return run(handler.handle(AssignEmployeeCommand(
        employee_id="emp1", directory_id=directory, site_id=site, start_date=start, end_date=end,
        actor_user_id="usr99", actor_role=actor_role.value)))


def run(coro):
    import asyncio

    return asyncio.run(coro)


def test_transfer_ends_current_assignment_the_day_before(write_side):
    _employee(write_side)
    current = _assignment(write_side, 1, date(2026, 10, 1))
    dto = _assign(write_side, date(2026, 11, 3))
    assert current.end_date == date(2026, 11, 2)
    assert (dto.start_date, dto.site_id) == (date(2026, 11, 3), "site2")


def test_transfer_on_same_start_day_cancels_current(write_side):
    _employee(write_side)
    current = _assignment(write_side, 1, TODAY)
    _assign(write_side, TODAY)
    assert current.is_cancelled
    assert run(write_side.assignments.find_active(EmployeeId("emp1"), TODAY)).site_id == SiteId("site2")


def test_future_assignment_conflict_is_409(write_side):
    _employee(write_side)
    _assignment(write_side, 1, date(2026, 10, 1), date(2026, 11, 30))
    _assignment(write_side, 2, date(2026, 12, 1))
    with pytest.raises(FutureAssignmentExistsError):
        _assign(write_side, date(2026, 11, 10))
    assert FutureAssignmentExistsError.http_status == 409


def test_start_in_past_is_422(write_side):
    _employee(write_side)
    with pytest.raises(AssignmentInPastError):
        _assign(write_side, date(2026, 10, 30))
    assert AssignmentInPastError.http_status == 422


def test_directory_outside_company_is_422(write_side):
    _employee(write_side)
    with pytest.raises(DirectoryOutsideCompanyError):
        _assign(write_side, TODAY, directory="dir9", site="site9")
    _assign(write_side, TODAY, directory="dir2", site="site2")  # a department of the company is fine


def test_inactive_employee_cannot_be_assigned(write_side):
    _employee(write_side, active=False)
    with pytest.raises(EmployeeInactiveError):
        _assign(write_side, TODAY)


def test_manager_cannot_assign_an_admin(write_side):
    _employee(write_side, role=Role.ADMIN)
    with pytest.raises(RoleCeilingError):
        _assign(write_side, TODAY, actor_role=Role.MANAGER)


def test_employee_role_cannot_assign(write_side):
    from identity.domain.errors import RolePermissionDeniedError

    _employee(write_side)
    with pytest.raises(RolePermissionDeniedError):
        _assign(write_side, TODAY, actor_role=Role.EMPLOYEE)


def test_punch_site_today_unchanged_by_future_transfer(write_side):
    _employee(write_side)
    _assignment(write_side, 1, date(2026, 10, 1))
    _assign(write_side, date(2026, 11, 7))
    assert run(write_side.assignments.find_active(EmployeeId("emp1"), TODAY)).site_id == SiteId("site1")
    assert run(write_side.assignments.find_active(EmployeeId("emp1"), date(2026, 11, 7))).site_id == SiteId("site2")

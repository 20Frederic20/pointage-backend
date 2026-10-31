"""The one-off backfill: every existing record active, with its company."""

import asyncio
from datetime import date

from identity.application.services import CompanyService
from identity.domain import DirectoryId, EmployeeAssignmentId, EmployeeId, SiteId, UserId
from identity.domain.entities import Employee, EmployeeAssignment
from scripts.activate_and_backfill_employees import backfill


def _seed(side, n, *, active, assigned_to=None):
    employee = side.employees.add(Employee(EmployeeId(f"emp{n}"), user_id=UserId(f"usr{n}"),
                                           employee_number=f"EMP{n:07d}", is_active=active))
    if assigned_to:
        side.assignments.add(EmployeeAssignment(EmployeeAssignmentId(f"asg{n}"), employee_id=employee.id,
                                                directory_id=DirectoryId(assigned_to), site_id=SiteId("site2"),
                                                start_date=date(2026, 1, 1)))
    return employee


def _run(side):
    return asyncio.run(backfill(list(side.employees.items.values()), side.employees, side.assignments,
                                CompanyService(side.directories)))


def test_backfill_activates_inactive_and_sets_company(write_side):
    inactive = _seed(write_side, 1, active=False, assigned_to="dir2")
    active = _seed(write_side, 2, active=True, assigned_to="dir1")
    assert _run(write_side) == (1, 2)
    assert (inactive.is_active, inactive.company_directory_id) == (True, DirectoryId("dir1"))
    assert active.company_directory_id == DirectoryId("dir1")


def test_backfill_is_idempotent(write_side):
    _seed(write_side, 1, active=False, assigned_to="dir2")
    _run(write_side)
    assert _run(write_side) == (0, 0)


def test_backfill_skips_company_without_assignment(write_side):
    lonely = _seed(write_side, 1, active=True)
    assert _run(write_side) == (0, 0)
    assert lonely.company_directory_id is None

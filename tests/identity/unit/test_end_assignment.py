"""Ending an assignment: same ceiling as assigning, never in the past, never a cancelled one."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from core.domain.errors import ConflictError
from identity.application.commands import EndEmployeeAssignmentCommand
from identity.application.handlers import EndEmployeeAssignmentHandler
from identity.domain import DirectoryId, EmployeeAssignmentId, EmployeeId, Role, SiteId, UserId
from identity.domain.entities import Employee, EmployeeAssignment
from identity.domain.errors import AssignmentInPastError, RoleCeilingError

TODAY = datetime.now(UTC).date()


def _seed(side, *, role=Role.EMPLOYEE, cancelled=False):
    side.employees.add(Employee(EmployeeId("emp1"), user_id=UserId("usr1"), employee_number="EMP0000001",
                                is_active=True, role=role, company_directory_id=DirectoryId("dir1")))
    side.assignments.add(EmployeeAssignment(EmployeeAssignmentId("asg1"), employee_id=EmployeeId("emp1"),
                                            directory_id=DirectoryId("dir1"), site_id=SiteId("site1"),
                                            start_date=TODAY - timedelta(days=30), cancelled=cancelled))


def _end(side, end_date, actor_role=Role.HR):
    handler = EndEmployeeAssignmentHandler(unit_of_work=side.unit_of_work, employee_assignment_repository=side.assignments,
                                           employee_repository=side.employees)
    return asyncio.run(handler.handle(EndEmployeeAssignmentCommand(
        employee_assignment_id="asg1", end_date=end_date, actor_user_id="usr99", actor_role=actor_role.value)))


def test_manager_cannot_end_an_admin_assignment(write_side):
    _seed(write_side, role=Role.ADMIN)
    with pytest.raises(RoleCeilingError):
        _end(write_side, TODAY, actor_role=Role.MANAGER)


def test_end_in_the_past_is_refused(write_side):
    _seed(write_side)
    with pytest.raises(AssignmentInPastError):
        _end(write_side, TODAY - timedelta(days=1))
    assert _end(write_side, TODAY).end_date == TODAY


def test_a_cancelled_assignment_cannot_be_ended(write_side):
    _seed(write_side, cancelled=True)
    with pytest.raises(ConflictError):
        _end(write_side, TODAY)

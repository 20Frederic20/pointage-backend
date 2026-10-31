"""Edit, deactivate and reactivate an employee record, under the role ceiling."""

import asyncio

import pytest

from identity.application.commands import EditEmployeeCommand, SetEmployeeActiveCommand
from identity.application.handlers import EditEmployeeHandler, SetEmployeeActiveHandler
from identity.domain import DirectoryId, EmployeeId, Role, UserId
from identity.domain.entities import Employee, User
from identity.domain.errors import AlreadyActiveInCompanyError, RoleCeilingError, SelfDeactivationError


def _seed(side, n, *, user=None, role=Role.EMPLOYEE, active=True, company="dir1"):
    user_id = UserId(user or f"usr{n}")
    if user_id not in side.users.items:
        side.users.add(User(user_id, email=f"u{n}@pointage.bj", password_hash=None, role=role,
                            first_name="Ana", last_name="Dossou", is_active=True))
    return side.employees.add(Employee(EmployeeId(f"emp{n}"), user_id=user_id, employee_number=f"EMP{n:07d}",
                                       is_active=active, role=role, company_directory_id=DirectoryId(company)))


def _edit(side, employee_id, *, actor="usr99", actor_role=Role.HR, **fields):
    handler = EditEmployeeHandler(unit_of_work=side.unit_of_work, employee_repository=side.employees,
                                  user_repository=side.users)
    command = EditEmployeeCommand(actor_user_id=actor, actor_role=actor_role.value, employee_id=employee_id,
                                  first_name=fields.get("first_name"), last_name=fields.get("last_name"),
                                  phone=fields.get("phone"), role=fields.get("role"))
    return asyncio.run(handler.handle(command))


def _set_active(side, employee_id, active, *, actor="usr99", actor_role=Role.HR):
    handler = SetEmployeeActiveHandler(unit_of_work=side.unit_of_work, employee_repository=side.employees)
    return asyncio.run(handler.handle(SetEmployeeActiveCommand(
        actor_user_id=actor, actor_role=actor_role.value, employee_id=employee_id, active=active)))


def test_edit_updates_user_names_and_employee_phone_and_role(write_side):
    _seed(write_side, 1)
    dto = _edit(write_side, "emp1", first_name="Awa", last_name="Kora", phone="0197000000", role=Role.MANAGER)
    user = write_side.users.items[UserId("usr1")]
    assert (user.first_name, user.last_name) == ("Awa", "Kora")
    assert (dto.phone, dto.role) == ("0197000000", Role.MANAGER)


def test_manager_cannot_grant_hr(write_side):
    _seed(write_side, 1)
    with pytest.raises(RoleCeilingError):
        _edit(write_side, "emp1", actor_role=Role.MANAGER, role=Role.HR)


def test_cannot_change_own_role(write_side):
    _seed(write_side, 1, user="usr99", role=Role.MANAGER)
    with pytest.raises(RoleCeilingError):
        _edit(write_side, "emp1", actor="usr99", actor_role=Role.ADMIN, role=Role.EMPLOYEE)
    _edit(write_side, "emp1", actor="usr99", actor_role=Role.ADMIN, phone="0197000000")  # other fields are fine


def test_manager_cannot_edit_or_deactivate_admin(write_side):
    _seed(write_side, 1, role=Role.ADMIN)
    with pytest.raises(RoleCeilingError):
        _edit(write_side, "emp1", actor_role=Role.MANAGER, phone="0197000000")
    with pytest.raises(RoleCeilingError):
        _set_active(write_side, "emp1", False, actor_role=Role.MANAGER)


def test_ceiling_uses_token_role_not_highest_record(write_side):
    _seed(write_side, 2, user="usr99", role=Role.ADMIN, company="dir9")  # the actor is ADMIN elsewhere
    _seed(write_side, 1)
    with pytest.raises(RoleCeilingError):
        _edit(write_side, "emp1", actor="usr99", actor_role=Role.MANAGER, role=Role.HR)


def test_cannot_deactivate_self(write_side):
    _seed(write_side, 1, user="usr99")
    with pytest.raises(SelfDeactivationError):
        _set_active(write_side, "emp1", False, actor="usr99")


def test_reactivate_refused_when_active_elsewhere_in_same_company(write_side):
    _seed(write_side, 1, user="usr5", active=False)
    _seed(write_side, 2, user="usr5", active=True)
    with pytest.raises(AlreadyActiveInCompanyError):
        _set_active(write_side, "emp1", True)


def test_deactivate_then_reactivate(write_side):
    _seed(write_side, 1)
    assert _set_active(write_side, "emp1", False).is_active is False
    assert _set_active(write_side, "emp1", True).is_active is True


def test_deactivate_keeps_assignments_and_user_account_active(write_side):
    from datetime import date

    from identity.domain import EmployeeAssignmentId, SiteId
    from identity.domain.entities import EmployeeAssignment

    _seed(write_side, 1)
    assignment = write_side.assignments.add(EmployeeAssignment(
        EmployeeAssignmentId("asg1"), employee_id=EmployeeId("emp1"), directory_id=DirectoryId("dir1"),
        site_id=SiteId("site1"), start_date=date(2026, 1, 1)))
    _set_active(write_side, "emp1", False)
    assert write_side.users.items[UserId("usr1")].is_active
    assert (assignment.end_date, assignment.is_cancelled) == (None, False)

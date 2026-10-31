from identity.application.handlers import GetEmployeeByIdHandler
from identity.application.queries import GetEmployeeByIdQuery
from identity.domain import Role


def _handle(run, repo, employee_id):
    return run(GetEmployeeByIdHandler(employee_repository=repo).handle(GetEmployeeByIdQuery(employee_id=employee_id)))


def test_known_id_returns_the_employee(run, in_memory, make_employee):
    repo = in_memory([make_employee(1), make_employee(2, role=Role.MANAGER)], "Employee")
    dto = _handle(run, repo, "emp2")
    assert (dto.id, dto.employee_number, dto.role, dto.user_id) == ("emp2", "EMP0000002", Role.MANAGER, "usr2")


def test_unknown_id_returns_none(run, in_memory, make_employee):
    assert _handle(run, in_memory([make_employee(1)], "Employee"), "emp999") is None


def test_malformed_id_returns_none_instead_of_raising(run, in_memory):
    assert _handle(run, in_memory([], "Employee"), "NOT-AN-ID") is None

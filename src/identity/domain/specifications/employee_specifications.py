from core.domain.specifications import Specification
from identity.domain import Role
from identity.domain.entities import Employee


class EmployeeEmployeeNumberrIs(Specification[Employee]):
    __slots__ = ("_employee_number",)

    def __init__(self, employee_number: str) -> None:
        self._employee_number = employee_number.strip().lower()

    def is_satisfied_by(self, candidate: Employee) -> bool:
        return candidate.employee_number == self._employee_number

    @property
    def employee_number(self) -> str:
        return self._employee_number


class EmployeeIsActiveIs(Specification[Employee]):
    __slots__ = ("_expected",)

    def __init__(self, expected: bool) -> None:
        self._expected = expected

    def is_satisfied_by(self, candidate: Employee) -> bool:
        return candidate.is_active is self._expected

    @property
    def expected(self) -> bool:
        return self._expected


class EmployeeRoleIs(Specification[Employee]):
    __slots__ = ("_expected",)

    def __init__(self, expected: Role) -> None:
        self._expected = expected

    def is_satisfied_by(self, candidate: Employee) -> bool:
        return candidate.role is self._expected

    @property
    def expected(self) -> Role:
        return self._expected
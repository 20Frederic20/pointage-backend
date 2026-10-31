"""Users-context leaf specifications → SQLAlchemy where-clauses."""

from sqlalchemy import func, ColumnElement

from core.domain.specifications import Specification
from core.infrastructure.specifications import (
    SqlAlchemySpecificationTranslator,
)

from ..domain.specifications import (
    EmployeeEmployeeNumberIs,
    EmployeeIsActiveIs,
    EmployeeRoleIs,
    EmployeeUserIs,
    UserEmailIs,
    UserIsActiveIs,
    UserRoleIs,
)
from .persistence.models import EmployeeModel, UserModel


class UsersSpecificationTranslator(SqlAlchemySpecificationTranslator):
    """The only place a users domain term meets a users column."""

    __slots__ = ()

    def translate_leaf(self, spec: Specification) -> ColumnElement[bool]:
        if isinstance(spec, UserEmailIs):
            return UserModel.email == spec.email
        if isinstance(spec, UserIsActiveIs):
            return UserModel.is_active.is_(spec.expected)
        if isinstance(spec, UserRoleIs):
            return UserModel.role == spec.expected
        raise TypeError(
            f"Unknown leaf specification {type(spec).__name__} — add a branch"
        )


class EmployeesSpecificationTranslator(SqlAlchemySpecificationTranslator):

    __slots__ = ()

    def translate_leaf(self, spec: Specification) -> ColumnElement[bool]:
        if isinstance(spec, EmployeeEmployeeNumberIs):
            return func.lower(EmployeeModel.employee_number) == spec.employee_number
        if isinstance(spec, EmployeeIsActiveIs):
            return EmployeeModel.is_active.is_(spec.expected)
        if isinstance(spec, EmployeeRoleIs):
            return EmployeeModel.role == spec.expected
        if isinstance(spec, EmployeeUserIs):
            return EmployeeModel.user_id == spec.user_id
        raise TypeError(
            f"Unknown leaf specification {type(spec).__name__} — add a branch"
        )
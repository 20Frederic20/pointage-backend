"""Users-context leaf specifications → SQLAlchemy where-clauses."""

from sqlalchemy import ColumnElement

from core.domain.specifications import Specification
from core.infrastructure.specifications import (
    SqlAlchemySpecificationTranslator,
)

from ..domain.specifications import (
    UserEmailIs,
    UserIsActiveIs,
    UserRoleIs,
)
from .persistence.models import UserModel


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

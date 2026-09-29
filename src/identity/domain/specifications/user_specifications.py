"""Leaf specifications over the User aggregate."""

from core.domain.specifications import Specification

from ..entities import User
from ..value_objects.role import Role


class UserEmailIs(Specification[User]):
    __slots__ = ("_email",)

    def __init__(self, email: str) -> None:
        self._email = email.strip().lower()

    def is_satisfied_by(self, candidate: User) -> bool:
        return candidate.email == self._email

    @property
    def email(self) -> str:
        return self._email


class UserIsActiveIs(Specification[User]):
    __slots__ = ("_expected",)

    def __init__(self, expected: bool) -> None:
        self._expected = expected

    def is_satisfied_by(self, candidate: User) -> bool:
        return candidate.is_active is self._expected

    @property
    def expected(self) -> bool:
        return self._expected


class UserRoleIs(Specification[User]):
    __slots__ = ("_expected",)

    def __init__(self, expected: Role) -> None:
        self._expected = expected

    def is_satisfied_by(self, candidate: User) -> bool:
        return candidate.role is self._expected

    @property
    def expected(self) -> Role:
        return self._expected
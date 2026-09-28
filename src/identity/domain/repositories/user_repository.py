"""Persistence port for the User aggregate."""

from abc import abstractmethod

from core.domain.repositories import IRepository
from core.domain.specifications import Specification

from ..entities import User
from ..value_objects.ids import DirectoryId, UserId


class IUserRepository(IRepository[User, UserId]):
    """User persistence, extended with the lookups the use cases need.

    In addition to the base aggregate protocol, callers need to: find a
    user by email (login), page through a workspace's members (inbox /
    admin screens), and count active members (seat-limit enforcement).
    """

    @abstractmethod
    async def find_by_email(self, email: str) -> User | None:
        """The user registered under ``email`` (case-insensitive), if any."""
        ...

    @abstractmethod
    async def find(
        self,
        spec: Specification[User],
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[User]:
        """Users matching ``spec``, paged — the specification is translated
        at the database by the infrastructure adapter, never filtered in
        Python after loading everything.
        """
        ...

    @abstractmethod
    async def count_active(self, directory_id: DirectoryId) -> int:
        """
        Active members of the workspace — the number a seat is bought against.
        """
        ...

    @abstractmethod
    async def count(self, spec: Specification[User]) -> int:
        """Users matching ``spec`` — the ``total`` of a paged listing, before
        limit/offset are applied."""
        ...

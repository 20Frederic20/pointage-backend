"""Paged member listing, filtered at the storage by specification."""

from core.application import QueryHandler
from core.domain.specifications import Specification

from ...domain.entities import User
from ...domain.repositories import IUserRepository
from ...domain.specifications import (
    UserIsActiveIs,
    UserRoleIs,
)
from ..dtos import UserDTO, UsersPageDTO
from ..queries import GetUsersQuery


class GetUsersHandler(QueryHandler[GetUsersQuery, UsersPageDTO]):
    """Combines the directory leaf spec with any optional filters and lets
    the repository translate the tree — no in-Python filtering."""

    def __init__(self, *, user_repository: IUserRepository) -> None:
        super().__init__()
        self._users = user_repository

    async def handle(self, request: GetUsersQuery) -> UsersPageDTO:
        spec: Specification[User] | None = None
        for leaf in (
            UserRoleIs(request.role) if request.role is not None else None,
            UserIsActiveIs(request.is_active)
            if request.is_active is not None
            else None,
        ):
            if leaf is not None:
                spec = leaf if spec is None else spec & leaf

        users = await self._users.find(
            spec, limit=request.limit, offset=request.offset
        )
        total = await self._users.count(spec)
        return UsersPageDTO(
            items=tuple(UserDTO.from_aggregate(u) for u in users),
            total=total,
        )

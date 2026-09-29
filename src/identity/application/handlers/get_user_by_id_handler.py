"""Load one member — workspace-scoped so cross-tenant ids read as missing."""

from core.application import QueryHandler
from core.domain.errors import NotFoundError

from ...domain.repositories import IUserRepository
from ...domain.value_objects.ids import UserId
from ..dtos import UserDTO
from ..queries import GetUserByIdQuery


class GetUserByIdHandler(QueryHandler[GetUserByIdQuery, UserDTO | None]):
    def __init__(self, *, user_repository: IUserRepository) -> None:
        super().__init__()
        self._users = user_repository

    async def handle(self, request: GetUserByIdQuery) -> UserDTO | None:
        try:
            user = await self._users.get_by_id(UserId(request.user_id))
        except NotFoundError:
            return None
        return UserDTO.from_aggregate(user)
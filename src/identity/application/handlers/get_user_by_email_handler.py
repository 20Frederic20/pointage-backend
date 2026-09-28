"""Login support: resolve an email to its credentials record, if any."""

from core.application import QueryHandler

from ...domain.repositories import IUserRepository
from ..dtos import UserCredentialsDTO
from ..queries import GetUserByEmailQuery


class GetUserByEmailHandler(
    QueryHandler[GetUserByEmailQuery, UserCredentialsDTO | None]
):
    """Returns ``None`` for unknown emails — callers run the dummy-hash path."""

    def __init__(self, *, user_repository: IUserRepository) -> None:
        super().__init__()
        self._users = user_repository

    async def handle(
        self, request: GetUserByEmailQuery
    ) -> UserCredentialsDTO | None:
        user = await self._users.find_by_email(request.email)
        if user is None:
            return None
        return UserCredentialsDTO.from_aggregate(user)
"""Page through a workspace's members."""

from dataclasses import dataclass

from core.application import Query

from ...domain.value_objects import Role
from ..dtos import UsersPageDTO


@dataclass(frozen=True)
class GetUsersQuery(Query):

    role: Role | None = None
    is_active: bool | None = None
    limit: int = 50
    offset: int = 0

    Result = UsersPageDTO
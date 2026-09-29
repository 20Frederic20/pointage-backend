"""Load one workspace member."""

from dataclasses import dataclass

from core.application import Query

from ..dtos import UserDTO


@dataclass(frozen=True)
class GetUserByIdQuery(Query):

    user_id: str

    Result = UserDTO | None
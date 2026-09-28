"""Load one workspace member."""

from dataclasses import dataclass

from core.application import Query

from ..dtos import UserDTO


@dataclass(frozen=True)
class GetUserByIdQuery(Query):
    """A member of ``directory_id``; cross-workspace ids read as missing."""

    directory_id: str
    user_id: str

    Result = UserDTO | None
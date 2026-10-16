"""Page through the directories."""

from dataclasses import dataclass

from core.application import Query

from ..dtos import DirectoriesPageDTO


@dataclass(frozen=True)
class GetDirectoriesQuery(Query):
    limit: int = 50
    offset: int = 0

    Result = DirectoriesPageDTO

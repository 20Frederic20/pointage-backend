"""Load one workspace."""

from dataclasses import dataclass

from core.application import Query

from ..dtos import DirectoryDTO


@dataclass(frozen=True)
class GetDirectoryByIdQuery(Query):
    directory_id: str

    Result = DirectoryDTO | None

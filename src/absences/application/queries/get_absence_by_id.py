"""Load one absence."""

from dataclasses import dataclass

from core.application import Query

from ..dtos import AbsenceDTO


@dataclass(frozen=True)
class GetAbsenceByIdQuery(Query):

    absence_id: str

    Result = AbsenceDTO | None

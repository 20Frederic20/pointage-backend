"""Load one time profile with its versions."""

from dataclasses import dataclass

from core.application import Query

from ..dtos import TimeProfileDTO


@dataclass(frozen=True)
class GetTimeProfileByIdQuery(Query):

    time_profile_id: str

    Result = TimeProfileDTO | None

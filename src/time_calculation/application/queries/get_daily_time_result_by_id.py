"""Load one daily time result."""

from dataclasses import dataclass

from core.application import Query

from ..dtos import DailyTimeResultDTO


@dataclass(frozen=True)
class GetDailyTimeResultByIdQuery(Query):

    daily_time_result_id: str

    Result = DailyTimeResultDTO | None

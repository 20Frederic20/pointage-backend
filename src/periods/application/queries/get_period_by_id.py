"""Load one period."""

from dataclasses import dataclass

from core.application import Query

from ..dtos import PeriodDTO


@dataclass(frozen=True)
class GetPeriodByIdQuery(Query):

    period_id: str

    Result = PeriodDTO | None

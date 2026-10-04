from datetime import date, datetime, timedelta

from pydantic import BaseModel, ConfigDict


class _CamelSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class CreateCalculationRuleVersionRequest(_CamelSchema):

    effective_from: date
    # Durations accept ISO 8601 ("PT30M") or a number of seconds.
    min_break_duration: timedelta
    break_threshold: timedelta
    max_daily_work_duration: timedelta
    max_amplitude: timedelta


class CalculationRuleVersionResponse(_CamelSchema):

    id: str
    rule_version: int
    effective_from: date
    effective_to: date | None = None
    min_break_duration: timedelta
    break_threshold: timedelta
    max_daily_work_duration: timedelta
    max_amplitude: timedelta
    created_at: datetime
    updated_at: datetime


class CalculateDailyTimeRequest(_CamelSchema):

    employee_id: str
    work_date: date


class RecalculatePeriodRequest(_CamelSchema):

    period_id: str


class DailyTimeResultResponse(_CamelSchema):

    id: str
    employee_id: str
    period_id: str
    calculation_rule_version_id: str
    work_date: date
    planned_duration: timedelta
    worked_duration: timedelta
    break_duration: timedelta
    absence_duration: timedelta
    late_duration: timedelta
    status: str
    calculated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PeriodRecalculationResponse(_CamelSchema):

    period_id: str
    recalculated_count: int
    skipped_validated_count: int

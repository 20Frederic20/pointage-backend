from datetime import date, datetime, timedelta

from core.domain.events import (
    BaseEvent,
    decode_date,
    decode_datetime,
    decode_timedelta,
    encode_date,
    encode_datetime,
    encode_timedelta,
)
from identity.domain.value_objects.ids import EmployeeId
from periods.domain.value_objects.ids import PeriodId

from ..value_objects import CalculationRuleVersionId, DailyResultStatus, DailyTimeResultId


class DailyTimeResultCalculated(BaseEvent[DailyTimeResultId]):
    """A daily result was calculated or recalculated; carries the computed values."""

    def __init__(
        self,
        daily_time_result_id: DailyTimeResultId,
        *,
        employee_id: EmployeeId,
        period_id: PeriodId,
        calculation_rule_version_id: CalculationRuleVersionId,
        work_date: date,
        planned_duration: timedelta,
        worked_duration: timedelta,
        break_duration: timedelta,
        absence_duration: timedelta,
        late_duration: timedelta,
        status: DailyResultStatus,
        calculated_at: datetime,
    ) -> None:
        super().__init__()
        self.daily_time_result_id = daily_time_result_id
        self.employee_id = employee_id
        self.period_id = period_id
        self.calculation_rule_version_id = calculation_rule_version_id
        self.work_date = work_date
        self.planned_duration = planned_duration
        self.worked_duration = worked_duration
        self.break_duration = break_duration
        self.absence_duration = absence_duration
        self.late_duration = late_duration
        self.status = status
        self.calculated_at = calculated_at

    def get_aggregate_id(self) -> DailyTimeResultId:
        return self.daily_time_result_id

    def get_event_name(self) -> str:
        return "time_calculation.daily_time_result.calculated"

    def to_payload(self) -> dict:
        return {
            "daily_time_result_id": self.daily_time_result_id.value,
            "employee_id": self.employee_id.value,
            "period_id": self.period_id.value,
            "calculation_rule_version_id": self.calculation_rule_version_id.value,
            "work_date": encode_date(self.work_date),
            "planned_duration": encode_timedelta(self.planned_duration),
            "worked_duration": encode_timedelta(self.worked_duration),
            "break_duration": encode_timedelta(self.break_duration),
            "absence_duration": encode_timedelta(self.absence_duration),
            "late_duration": encode_timedelta(self.late_duration),
            "status": self.status.value,
            "calculated_at": encode_datetime(self.calculated_at),
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "DailyTimeResultCalculated":
        return cls(
            DailyTimeResultId(payload["daily_time_result_id"]),
            employee_id=EmployeeId(payload["employee_id"]),
            period_id=PeriodId(payload["period_id"]),
            calculation_rule_version_id=CalculationRuleVersionId(payload["calculation_rule_version_id"]),
            work_date=decode_date(payload["work_date"]),
            planned_duration=decode_timedelta(payload["planned_duration"]),
            worked_duration=decode_timedelta(payload["worked_duration"]),
            break_duration=decode_timedelta(payload["break_duration"]),
            absence_duration=decode_timedelta(payload["absence_duration"]),
            late_duration=decode_timedelta(payload["late_duration"]),
            status=DailyResultStatus(payload["status"]),
            calculated_at=decode_datetime(payload["calculated_at"]),
        )


class DailyTimeResultValidated(BaseEvent[DailyTimeResultId]):
    """A daily result was validated (status becomes VALIDATED, nothing else changes)."""

    def __init__(self, daily_time_result_id: DailyTimeResultId) -> None:
        super().__init__()
        self.daily_time_result_id = daily_time_result_id

    def get_aggregate_id(self) -> DailyTimeResultId:
        return self.daily_time_result_id

    def get_event_name(self) -> str:
        return "time_calculation.daily_time_result.validated"

    def to_payload(self) -> dict:
        return {"daily_time_result_id": self.daily_time_result_id.value}

    @classmethod
    def from_payload(cls, payload: dict) -> "DailyTimeResultValidated":
        return cls(DailyTimeResultId(payload["daily_time_result_id"]))


class DailyTimeResultImported(BaseEvent[DailyTimeResultId]):
    """A daily result taken over from the state tables when event sourcing started."""

    def __init__(
        self,
        daily_time_result_id: DailyTimeResultId,
        *,
        employee_id: EmployeeId,
        period_id: PeriodId,
        calculation_rule_version_id: CalculationRuleVersionId,
        work_date: date,
        planned_duration: timedelta,
        worked_duration: timedelta,
        break_duration: timedelta,
        absence_duration: timedelta,
        late_duration: timedelta,
        status: DailyResultStatus,
        calculated_at: datetime | None,
        created_at: datetime,
    ) -> None:
        super().__init__()
        self.daily_time_result_id = daily_time_result_id
        self.employee_id = employee_id
        self.period_id = period_id
        self.calculation_rule_version_id = calculation_rule_version_id
        self.work_date = work_date
        self.planned_duration = planned_duration
        self.worked_duration = worked_duration
        self.break_duration = break_duration
        self.absence_duration = absence_duration
        self.late_duration = late_duration
        self.status = status
        self.calculated_at = calculated_at
        self.created_at = created_at

    def get_aggregate_id(self) -> DailyTimeResultId:
        return self.daily_time_result_id

    def get_event_name(self) -> str:
        return "time_calculation.daily_time_result.imported"

    def to_payload(self) -> dict:
        return {
            "daily_time_result_id": self.daily_time_result_id.value,
            "employee_id": self.employee_id.value,
            "period_id": self.period_id.value,
            "calculation_rule_version_id": self.calculation_rule_version_id.value,
            "work_date": encode_date(self.work_date),
            "planned_duration": encode_timedelta(self.planned_duration),
            "worked_duration": encode_timedelta(self.worked_duration),
            "break_duration": encode_timedelta(self.break_duration),
            "absence_duration": encode_timedelta(self.absence_duration),
            "late_duration": encode_timedelta(self.late_duration),
            "status": self.status.value,
            "calculated_at": encode_datetime(self.calculated_at),
            "created_at": encode_datetime(self.created_at),
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "DailyTimeResultImported":
        return cls(
            DailyTimeResultId(payload["daily_time_result_id"]),
            employee_id=EmployeeId(payload["employee_id"]),
            period_id=PeriodId(payload["period_id"]),
            calculation_rule_version_id=CalculationRuleVersionId(payload["calculation_rule_version_id"]),
            work_date=decode_date(payload["work_date"]),
            planned_duration=decode_timedelta(payload["planned_duration"]),
            worked_duration=decode_timedelta(payload["worked_duration"]),
            break_duration=decode_timedelta(payload["break_duration"]),
            absence_duration=decode_timedelta(payload["absence_duration"]),
            late_duration=decode_timedelta(payload["late_duration"]),
            status=DailyResultStatus(payload["status"]),
            calculated_at=decode_datetime(payload["calculated_at"]),
            created_at=decode_datetime(payload["created_at"]),
        )

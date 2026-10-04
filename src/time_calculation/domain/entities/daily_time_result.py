from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta

from core.domain.entity import AggregateRoot
from identity.domain import EmployeeId
from periods.domain import PeriodId

from ..errors import BlockedDailyTimeResultError, DailyTimeResultValidatedError
from ..events import DailyTimeResultCalculated, DailyTimeResultValidated
from ..services.daily_time_calculator import Clocking, DailyTimeCalculator, Interval
from ..value_objects import CalculationRuleVersionId, DailyResultStatus, DailyTimeResultId, PlannedDay
from .calculation_rule_version import CalculationRuleVersion


class DailyTimeResult(AggregateRoot[DailyTimeResultId]):
    """The calculated time of one employee on one work date."""

    __slots__ = (
        "_absence_duration",
        "_break_duration",
        "_calculated_at",
        "_calculation_rule_version_id",
        "_employee_id",
        "_late_duration",
        "_period_id",
        "_planned_duration",
        "_status",
        "_work_date",
        "_worked_duration",
    )

    def __init__(
        self,
        daily_time_result_id: DailyTimeResultId,
        *,
        employee_id: EmployeeId,
        period_id: PeriodId,
        calculation_rule_version_id: CalculationRuleVersionId,
        work_date: date,
        planned_duration: timedelta = timedelta(0),
        worked_duration: timedelta = timedelta(0),
        break_duration: timedelta = timedelta(0),
        absence_duration: timedelta = timedelta(0),
        late_duration: timedelta = timedelta(0),
        status: DailyResultStatus = DailyResultStatus.NORMAL,
        calculated_at: datetime | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        version: int = 0,
    ) -> None:
        super().__init__(daily_time_result_id, created_at=created_at, updated_at=updated_at, version=version)
        self._employee_id = employee_id
        self._period_id = period_id
        self._calculation_rule_version_id = calculation_rule_version_id
        self._work_date = work_date
        self._planned_duration = planned_duration
        self._worked_duration = worked_duration
        self._break_duration = break_duration
        self._absence_duration = absence_duration
        self._late_duration = late_duration
        self._status = DailyResultStatus(status)
        self._calculated_at = calculated_at

    @classmethod
    def calculate(
        cls,
        daily_time_result_id: DailyTimeResultId,
        *,
        employee_id: EmployeeId,
        period_id: PeriodId,
        work_date: date,
        rules: CalculationRuleVersion,
        planned_day: PlannedDay | None,
        clockings: Sequence[Clocking],
        absences: Sequence[Interval],
        has_open_blocking_anomaly: bool,
        has_open_anomaly: bool,
    ) -> "DailyTimeResult":
        """``calculer``: the first calculation of a work date."""
        result = cls(
            daily_time_result_id,
            employee_id=employee_id,
            period_id=period_id,
            calculation_rule_version_id=rules.id,
            work_date=work_date,
        )
        result._apply(
            rules=rules,
            planned_day=planned_day,
            clockings=clockings,
            absences=absences,
            has_open_blocking_anomaly=has_open_blocking_anomaly,
            has_open_anomaly=has_open_anomaly,
        )
        return result

    def recalculate(
        self,
        *,
        period_id: PeriodId,
        rules: CalculationRuleVersion,
        planned_day: PlannedDay | None,
        clockings: Sequence[Clocking],
        absences: Sequence[Interval],
        has_open_blocking_anomaly: bool,
        has_open_anomaly: bool,
    ) -> None:
        """``recalculer``: refresh an existing result; a validated one is final."""
        if self._status == DailyResultStatus.VALIDATED:
            raise DailyTimeResultValidatedError(
                f"Daily result of {self._work_date} is validated and cannot be recalculated",
                context=self.id.value,
            )
        self._period_id = period_id
        self._calculation_rule_version_id = rules.id
        self._apply(
            rules=rules,
            planned_day=planned_day,
            clockings=clockings,
            absences=absences,
            has_open_blocking_anomaly=has_open_blocking_anomaly,
            has_open_anomaly=has_open_anomaly,
        )

    def validate(self) -> None:
        if self._status == DailyResultStatus.VALIDATED:
            raise DailyTimeResultValidatedError(
                f"Daily result of {self._work_date} is already validated", context=self.id.value
            )
        if self._status == DailyResultStatus.BLOCKED:
            raise BlockedDailyTimeResultError(
                f"Daily result of {self._work_date} is blocked by an open blocking anomaly",
                context=self.id.value,
            )
        self._status = DailyResultStatus.VALIDATED
        self.touch()
        self.record_event(DailyTimeResultValidated(self.id))

    def _apply(
        self,
        *,
        rules: CalculationRuleVersion,
        planned_day: PlannedDay | None,
        clockings: Sequence[Clocking],
        absences: Sequence[Interval],
        has_open_blocking_anomaly: bool,
        has_open_anomaly: bool,
    ) -> None:
        worked, breaks, has_unpaired = DailyTimeCalculator.worked_time(clockings)
        worked, breaks = DailyTimeCalculator.enforce_minimum_break(
            worked,
            breaks,
            break_threshold=rules.break_threshold,
            min_break_duration=rules.min_break_duration,
        )
        has_overrun = DailyTimeCalculator.has_overrun(
            worked,
            clockings,
            max_daily_work_duration=rules.max_daily_work_duration,
            max_amplitude=rules.max_amplitude,
        )
        self._planned_duration = planned_day.planned_duration if planned_day is not None else timedelta(0)
        self._worked_duration = worked
        self._break_duration = breaks
        self._absence_duration = DailyTimeCalculator.absence_time(planned_day, absences)
        self._late_duration = DailyTimeCalculator.lateness(clockings, planned_day, absences)
        if has_open_blocking_anomaly:
            self._status = DailyResultStatus.BLOCKED
        elif has_unpaired or has_overrun or has_open_anomaly:
            self._status = DailyResultStatus.ANOMALY
        else:
            self._status = DailyResultStatus.NORMAL
        self._calculated_at = datetime.now(UTC)
        self.touch()
        self.record_event(DailyTimeResultCalculated(self.id))

    @property
    def employee_id(self) -> EmployeeId:
        return self._employee_id

    @property
    def period_id(self) -> PeriodId:
        return self._period_id

    @property
    def calculation_rule_version_id(self) -> CalculationRuleVersionId:
        return self._calculation_rule_version_id

    @property
    def work_date(self) -> date:
        return self._work_date

    @property
    def planned_duration(self) -> timedelta:
        return self._planned_duration

    @property
    def worked_duration(self) -> timedelta:
        return self._worked_duration

    @property
    def break_duration(self) -> timedelta:
        return self._break_duration

    @property
    def absence_duration(self) -> timedelta:
        return self._absence_duration

    @property
    def late_duration(self) -> timedelta:
        return self._late_duration

    @property
    def status(self) -> DailyResultStatus:
        return self._status

    @property
    def calculated_at(self) -> datetime | None:
        return self._calculated_at

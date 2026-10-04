from datetime import date, datetime, timedelta

from core.domain.entity import AggregateRoot

from ..errors import InvalidCalculationRuleVersionError
from ..events import CalculationRuleVersionCreated
from ..value_objects import CalculationRuleVersionId


class CalculationRuleVersion(AggregateRoot[CalculationRuleVersionId]):
    """Dated calculation thresholds.

    * past ``break_threshold`` of work, a break shorter than ``min_break_duration``
      is completed out of worked time;
    * worked time above ``max_daily_work_duration`` or a day spanning more than
      ``max_amplitude`` is an overrun.
    """

    __slots__ = (
        "_break_threshold",
        "_effective_from",
        "_effective_to",
        "_max_amplitude",
        "_max_daily_work_duration",
        "_min_break_duration",
        "_rule_version",
    )

    def __init__(
        self,
        calculation_rule_version_id: CalculationRuleVersionId,
        *,
        rule_version: int,
        effective_from: date,
        effective_to: date | None,
        min_break_duration: timedelta,
        break_threshold: timedelta,
        max_daily_work_duration: timedelta,
        max_amplitude: timedelta,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        version: int = 0,
    ) -> None:
        super().__init__(calculation_rule_version_id, created_at=created_at, updated_at=updated_at, version=version)
        if min(min_break_duration, break_threshold) < timedelta(0):
            raise InvalidCalculationRuleVersionError(
                "Break duration and break threshold cannot be negative",
                context=calculation_rule_version_id.value,
            )
        if min(max_daily_work_duration, max_amplitude) <= timedelta(0):
            raise InvalidCalculationRuleVersionError(
                "Maximum daily work duration and maximum amplitude must be positive",
                context=calculation_rule_version_id.value,
            )
        if effective_to is not None and effective_to < effective_from:
            raise InvalidCalculationRuleVersionError(
                f"Rule version ends ({effective_to}) before it starts ({effective_from})",
                context=calculation_rule_version_id.value,
            )
        self._rule_version = rule_version
        self._effective_from = effective_from
        self._effective_to = effective_to
        self._min_break_duration = min_break_duration
        self._break_threshold = break_threshold
        self._max_daily_work_duration = max_daily_work_duration
        self._max_amplitude = max_amplitude

    @classmethod
    def create(
        cls,
        calculation_rule_version_id: CalculationRuleVersionId,
        *,
        previous: "CalculationRuleVersion | None",
        effective_from: date,
        min_break_duration: timedelta,
        break_threshold: timedelta,
        max_daily_work_duration: timedelta,
        max_amplitude: timedelta,
    ) -> "CalculationRuleVersion":
        """A new version after ``previous``, which then ends the day before."""
        if previous is not None:
            if effective_from <= previous.effective_from:
                raise InvalidCalculationRuleVersionError(
                    f"Rule version must start after {previous.effective_from}",
                    context=previous.id.value,
                )
            if previous.effective_to is None or previous.effective_to >= effective_from:
                previous.close(effective_from - timedelta(days=1))
        rule_version = cls(
            calculation_rule_version_id,
            rule_version=previous.rule_version + 1 if previous is not None else 1,
            effective_from=effective_from,
            effective_to=None,
            min_break_duration=min_break_duration,
            break_threshold=break_threshold,
            max_daily_work_duration=max_daily_work_duration,
            max_amplitude=max_amplitude,
        )
        rule_version.record_event(CalculationRuleVersionCreated(calculation_rule_version_id))
        return rule_version

    def is_applicable(self, day: date) -> bool:
        """``estApplicable``."""
        return self._effective_from <= day and (self._effective_to is None or day <= self._effective_to)

    def close(self, last_day: date) -> None:
        if last_day < self._effective_from:
            raise InvalidCalculationRuleVersionError(
                f"Rule version cannot end ({last_day}) before it starts ({self._effective_from})",
                context=self.id.value,
            )
        self._effective_to = last_day
        self.touch()

    @property
    def rule_version(self) -> int:
        return self._rule_version

    @property
    def effective_from(self) -> date:
        return self._effective_from

    @property
    def effective_to(self) -> date | None:
        return self._effective_to

    @property
    def min_break_duration(self) -> timedelta:
        return self._min_break_duration

    @property
    def break_threshold(self) -> timedelta:
        return self._break_threshold

    @property
    def max_daily_work_duration(self) -> timedelta:
        return self._max_daily_work_duration

    @property
    def max_amplitude(self) -> timedelta:
        return self._max_amplitude

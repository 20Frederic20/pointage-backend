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

from ..value_objects import CalculationRuleVersionId


class CalculationRuleVersionCreated(BaseEvent[CalculationRuleVersionId]):
    """A new calculation rule version was created."""

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
    ) -> None:
        super().__init__()
        self.calculation_rule_version_id = calculation_rule_version_id
        self.rule_version = rule_version
        self.effective_from = effective_from
        self.effective_to = effective_to
        self.min_break_duration = min_break_duration
        self.break_threshold = break_threshold
        self.max_daily_work_duration = max_daily_work_duration
        self.max_amplitude = max_amplitude

    def get_aggregate_id(self) -> CalculationRuleVersionId:
        return self.calculation_rule_version_id

    def get_event_name(self) -> str:
        return "time_calculation.calculation_rule_version.created"

    def to_payload(self) -> dict:
        return {
            "calculation_rule_version_id": self.calculation_rule_version_id.value,
            "rule_version": self.rule_version,
            "effective_from": encode_date(self.effective_from),
            "effective_to": encode_date(self.effective_to),
            "min_break_duration": encode_timedelta(self.min_break_duration),
            "break_threshold": encode_timedelta(self.break_threshold),
            "max_daily_work_duration": encode_timedelta(self.max_daily_work_duration),
            "max_amplitude": encode_timedelta(self.max_amplitude),
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "CalculationRuleVersionCreated":
        return cls(
            CalculationRuleVersionId(payload["calculation_rule_version_id"]),
            rule_version=payload["rule_version"],
            effective_from=decode_date(payload["effective_from"]),
            effective_to=decode_date(payload["effective_to"]),
            min_break_duration=decode_timedelta(payload["min_break_duration"]),
            break_threshold=decode_timedelta(payload["break_threshold"]),
            max_daily_work_duration=decode_timedelta(payload["max_daily_work_duration"]),
            max_amplitude=decode_timedelta(payload["max_amplitude"]),
        )


class CalculationRuleVersionClosed(BaseEvent[CalculationRuleVersionId]):
    """A rule version got its last day (a newer version starts the day after)."""

    def __init__(self, calculation_rule_version_id: CalculationRuleVersionId, *, effective_to: date) -> None:
        super().__init__()
        self.calculation_rule_version_id = calculation_rule_version_id
        self.effective_to = effective_to

    def get_aggregate_id(self) -> CalculationRuleVersionId:
        return self.calculation_rule_version_id

    def get_event_name(self) -> str:
        return "time_calculation.calculation_rule_version.closed"

    def to_payload(self) -> dict:
        return {
            "calculation_rule_version_id": self.calculation_rule_version_id.value,
            "effective_to": encode_date(self.effective_to),
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "CalculationRuleVersionClosed":
        return cls(
            CalculationRuleVersionId(payload["calculation_rule_version_id"]),
            effective_to=decode_date(payload["effective_to"]),
        )


class CalculationRuleVersionImported(BaseEvent[CalculationRuleVersionId]):
    """A rule version taken over from the state tables when event sourcing started."""

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
        created_at: datetime,
    ) -> None:
        super().__init__()
        self.calculation_rule_version_id = calculation_rule_version_id
        self.rule_version = rule_version
        self.effective_from = effective_from
        self.effective_to = effective_to
        self.min_break_duration = min_break_duration
        self.break_threshold = break_threshold
        self.max_daily_work_duration = max_daily_work_duration
        self.max_amplitude = max_amplitude
        self.created_at = created_at

    def get_aggregate_id(self) -> CalculationRuleVersionId:
        return self.calculation_rule_version_id

    def get_event_name(self) -> str:
        return "time_calculation.calculation_rule_version.imported"

    def to_payload(self) -> dict:
        return {
            "calculation_rule_version_id": self.calculation_rule_version_id.value,
            "rule_version": self.rule_version,
            "effective_from": encode_date(self.effective_from),
            "effective_to": encode_date(self.effective_to),
            "min_break_duration": encode_timedelta(self.min_break_duration),
            "break_threshold": encode_timedelta(self.break_threshold),
            "max_daily_work_duration": encode_timedelta(self.max_daily_work_duration),
            "max_amplitude": encode_timedelta(self.max_amplitude),
            "created_at": encode_datetime(self.created_at),
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "CalculationRuleVersionImported":
        return cls(
            CalculationRuleVersionId(payload["calculation_rule_version_id"]),
            rule_version=payload["rule_version"],
            effective_from=decode_date(payload["effective_from"]),
            effective_to=decode_date(payload["effective_to"]),
            min_break_duration=decode_timedelta(payload["min_break_duration"]),
            break_threshold=decode_timedelta(payload["break_threshold"]),
            max_daily_work_duration=decode_timedelta(payload["max_daily_work_duration"]),
            max_amplitude=decode_timedelta(payload["max_amplitude"]),
            created_at=decode_datetime(payload["created_at"]),
        )

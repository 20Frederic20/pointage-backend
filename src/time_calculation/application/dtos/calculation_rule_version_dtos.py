from dataclasses import dataclass
from datetime import date, datetime, timedelta

from core.application import DTO

from ...domain.entities import CalculationRuleVersion


@dataclass(frozen=True)
class CalculationRuleVersionDTO(DTO):
    id: str
    rule_version: int
    effective_from: date
    effective_to: date | None
    min_break_duration: timedelta
    break_threshold: timedelta
    max_daily_work_duration: timedelta
    max_amplitude: timedelta
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_aggregate(cls, calculation_rule_version: CalculationRuleVersion) -> "CalculationRuleVersionDTO":
        return cls(
            id=calculation_rule_version.id.value,
            rule_version=calculation_rule_version.rule_version,
            effective_from=calculation_rule_version.effective_from,
            effective_to=calculation_rule_version.effective_to,
            min_break_duration=calculation_rule_version.min_break_duration,
            break_threshold=calculation_rule_version.break_threshold,
            max_daily_work_duration=calculation_rule_version.max_daily_work_duration,
            max_amplitude=calculation_rule_version.max_amplitude,
            created_at=calculation_rule_version.created_at,
            updated_at=calculation_rule_version.updated_at,
        )

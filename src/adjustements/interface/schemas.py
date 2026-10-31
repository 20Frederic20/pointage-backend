"""Wire schemas of the anomalies back-office API (camelCase JSON contract)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from ..domain.value_objects import AnomalyStatus, AnomalyType, Severity


class _CamelSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class AnomalyDecisionRequest(_CamelSchema):
    """``comment`` is optional to validate, required (non-blank) to reject:
    the domain decides, so a missing one is ``DECISION_COMMENT_REQUIRED``."""

    comment: str | None = None


class AnomalyItemResponse(_CamelSchema):
    id: str
    type: AnomalyType
    severity: Severity
    status: AnomalyStatus
    detected_at: datetime
    employee_id: str | None = None
    employee_number: str | None = None
    employee_first_name: str | None = None
    employee_last_name: str | None = None
    assisted_by_first_name: str | None = None
    assisted_by_last_name: str | None = None
    occured_at: datetime | None = None
    entry_type: str | None = None
    has_photo: bool = False
    decided_at: datetime | None = None
    decision_comment: str | None = None
    site_name: str | None = None


class AnomalyListResponse(_CamelSchema):
    items: list[AnomalyItemResponse]
    total: int

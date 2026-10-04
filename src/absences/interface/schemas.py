from datetime import datetime, timedelta

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class _CamelSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class CreateAbsenceTypeRequest(_CamelSchema):

    name: str = Field(min_length=1, max_length=100)
    paid: bool
    counts_as_work_time: bool
    deducts_balance: bool


class AbsenceTypeResponse(_CamelSchema):

    id: str
    name: str
    paid: bool
    counts_as_work_time: bool
    deducts_balance: bool
    active: bool
    created_at: datetime
    updated_at: datetime


class DeclareAbsenceRequest(_CamelSchema):

    employee_id: str
    absence_type_id: str
    # Timezone required: absences are compared with UTC-stored anomalies.
    start_at: AwareDatetime
    end_at: AwareDatetime
    reason: str = Field(min_length=1, max_length=512)
    justification_reference: str | None = Field(default=None, max_length=255)


class NeutralizeAnomalyRequest(_CamelSchema):

    anomaly_id: str


class AbsenceResponse(_CamelSchema):

    id: str
    employee_id: str
    absence_type_id: str
    start_at: datetime
    end_at: datetime
    duration: timedelta
    reason: str
    status: str
    justification_reference: str | None = None
    created_at: datetime
    updated_at: datetime

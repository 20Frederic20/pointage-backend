from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from punch.domain import EntrySource, LocationConfidence


class _CamelSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class CreateTimeEntryRequest(_CamelSchema):
    """The employee comes from the access token; IN / OUT is decided by the server."""

    longitude: float
    latitude: float
    source: EntrySource
    idempotency_key: str = Field(min_length=1, max_length=255)
    wifi_identifier: str | None = Field(default=None, max_length=255)


class CreateManagerTimeEntryRequest(_CamelSchema):
    """Only the retry key: the time and the direction are decided by the server."""

    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=255)


class TimeEntryResponse(_CamelSchema):

    id: str
    occured_at: datetime
    employee_id: str
    entry_type: str
    source: EntrySource
    created_at: datetime
    updated_at: datetime
    location_confidence: LocationConfidence | None = None
    idempotency_key: str | None = None
    wifi_identifier: str | None = None
    assisted_by_user_id: str | None = None
    validation_status: str = "COUNTED"


class TimeEntryListResponse(_CamelSchema):

    time_entries: list[TimeEntryResponse]
    total: int


class EmployeeLookupResponse(_CamelSchema):
    """Names only: enough for the colleague to confirm "C'est moi"."""

    employee_number: str = Field(alias="employeeNumber")
    first_name: str | None = Field(default=None, alias="firstName")
    last_name: str | None = Field(default=None, alias="lastName")

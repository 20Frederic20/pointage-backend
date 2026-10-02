from datetime import datetime

from pydantic import BaseModel, ConfigDict

from punch.domain import EntrySource, LocationConfidence


class _CamelSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class CreateTimeEntryRequest(_CamelSchema):

    employee_number: str
    longitude: float
    latitude: float
    source: EntrySource
    idempotency_key: str
    wifi_identifier: str | None = None
    location_confidence: LocationConfidence | None = None


class TimeEntryResponse(_CamelSchema):

    id: str
    occured_at: datetime
    employee_id: str
    entry_type: str
    source: EntrySource
    created_at: str
    updated_at: str
    location_confidence: LocationConfidence | None = None
    idempotency_key: str | None = None
    wifi_identifier: str | None = None


class TimeEntryListResponse(_CamelSchema):

    time_entries: list[TimeEntryResponse]
    total: int
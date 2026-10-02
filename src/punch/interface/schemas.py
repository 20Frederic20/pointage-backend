from datetime import datetime

from pydantic import ConfigDict

from core.infrastructure.database import BaseModel
from punch.domain import EntrySource, LocationConfidence


class _CamelSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class CreateTimeEntryRequest(_CamelSchema):

    employee_number: str
    longitude: float
    latitude: float
    source: EntrySource
    idempotency_key: str
    wifi_identifier: str
    location_confidence: LocationConfidence


class CreateTimeEntryResponse(_CamelSchema):

    id: str
    occured_at: datetime
    employee_id: str
    entry_type: str
    location_confidence: LocationConfidence
    source: EntrySource
    created_at: str
    updated_at: str
    idempotency_key: str | None = None
    wifi_identifier: str | None = None
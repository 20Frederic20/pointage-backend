from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class _CamelSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class OpenPeriodRequest(_CamelSchema):

    start_date: date
    end_date: date


class PeriodResponse(_CamelSchema):

    id: str
    start_date: date
    end_date: date
    status: str
    closed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

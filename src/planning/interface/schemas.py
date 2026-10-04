from datetime import date, datetime, time, timedelta

from pydantic import BaseModel, ConfigDict, Field

from planning.domain import DayOfWeek


class _CamelSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class CreateTimeProfileRequest(_CamelSchema):

    name: str = Field(min_length=1, max_length=100)
    # IANA timezone the profile's times of day are expressed in.
    timezone: str = Field(min_length=1, max_length=64, examples=["Africa/Porto-Novo"])


class TimeProfileDayRequest(_CamelSchema):

    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    # Durations accept ISO 8601 ("PT1H") or a number of seconds.
    break_duration: timedelta = timedelta(0)
    break_threshold: timedelta = timedelta(0)
    tolerance: timedelta = timedelta(0)


class AddTimeProfileVersionRequest(_CamelSchema):

    effective_from: date
    days: list[TimeProfileDayRequest] = Field(min_length=1, max_length=7)


class TimeProfileDayResponse(_CamelSchema):

    id: str
    day_of_week: str
    start_time: time
    end_time: time
    break_duration: timedelta
    break_threshold: timedelta
    tolerance: timedelta
    planned_duration: timedelta


class TimeProfileVersionResponse(_CamelSchema):

    id: str
    version: int
    effective_from: date
    effective_to: date | None = None
    days: list[TimeProfileDayResponse]


class TimeProfileResponse(_CamelSchema):

    id: str
    name: str
    timezone: str
    active: bool
    versions: list[TimeProfileVersionResponse]
    created_at: datetime
    updated_at: datetime


class AssignEmployeeScheduleRequest(_CamelSchema):

    employee_id: str
    time_profile_version_id: str
    start_date: date
    end_date: date | None = None


class EndEmployeeScheduleRequest(_CamelSchema):

    end_date: date


class EmployeeScheduleResponse(_CamelSchema):

    id: str
    employee_id: str
    time_profile_version_id: str
    start_date: date
    end_date: date | None = None
    created_at: datetime
    updated_at: datetime

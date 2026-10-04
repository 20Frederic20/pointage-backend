from typing import Literal

from core.domain.value_objects import EntityId


class TimeProfileId(EntityId[Literal["time_profile"]]):
    ...


class TimeProfileVersionId(EntityId[Literal["time_profile_version"]]):
    ...


class TimeProfileDayId(EntityId[Literal["time_profile_day"]]):
    ...


class EmployeeScheduleId(EntityId[Literal["employee_schedule"]]):
    ...

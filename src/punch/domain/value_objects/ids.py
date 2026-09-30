from typing import Literal

from core.domain.value_objects import EntityId


class TimeEntryId(EntityId[Literal["time_entry"]]):
    ...
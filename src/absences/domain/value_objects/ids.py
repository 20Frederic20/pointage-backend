from typing import Literal

from core.domain.value_objects import EntityId


class AbsenceId(EntityId[Literal["absence"]]):
    ...


class AbsenceTypeId(EntityId[Literal["absence_type"]]):
    ...

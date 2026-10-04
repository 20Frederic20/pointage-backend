from core.domain.repositories import IRepository

from ..entities import AbsenceType
from ..value_objects import AbsenceTypeId


class IAbsenceTypeRepository(IRepository[AbsenceType, AbsenceTypeId]):
    ...

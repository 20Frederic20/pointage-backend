from core.domain.repositories import IRepository

from ..entities import Absence
from ..value_objects import AbsenceId


class IAbsenceRepository(IRepository[Absence, AbsenceId]):
    ...

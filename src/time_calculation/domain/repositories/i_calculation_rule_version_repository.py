from abc import abstractmethod
from datetime import date

from core.domain.repositories import IRepository

from ..entities import CalculationRuleVersion
from ..value_objects import CalculationRuleVersionId


class ICalculationRuleVersionRepository(IRepository[CalculationRuleVersion, CalculationRuleVersionId]):

    @abstractmethod
    async def find_applicable(self, day: date) -> CalculationRuleVersion | None:
        ...

    @abstractmethod
    async def find_latest(self) -> CalculationRuleVersion | None:
        ...

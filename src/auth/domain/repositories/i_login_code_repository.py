from abc import abstractmethod
from datetime import datetime

from core.domain.repositories import IRepository

from ..entities import LoginCode
from ..value_objects import LoginCodeId


class ILoginCodeRepository(IRepository[LoginCode, LoginCodeId]):

    @abstractmethod
    async def find_latest_for_user(self, user_id: str) -> LoginCode | None:
        ...

    @abstractmethod
    async def count_issued_since(self, user_id: str, since: datetime) -> int:
        ...

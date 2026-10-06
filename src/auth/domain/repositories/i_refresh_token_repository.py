from abc import abstractmethod

from core.domain.repositories import IRepository

from ..entities import RefreshToken
from ..value_objects import RefreshTokenId, TokenFamilyId


class IRefreshTokenRepository(IRepository[RefreshToken, RefreshTokenId]):

    @abstractmethod
    async def find_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        ...

    @abstractmethod
    async def find_active_by_family(self, family_id: TokenFamilyId) -> list[RefreshToken]:
        """Tokens of ``family_id`` not revoked yet (expired ones included)."""
        ...

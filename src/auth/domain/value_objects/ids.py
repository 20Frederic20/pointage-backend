from typing import Literal

from core.domain.value_objects import EntityId


class RefreshTokenId(EntityId[Literal["refresh_token"]]):
    ...


class LoginCodeId(EntityId[Literal["login_code"]]):
    ...


class TokenFamilyId(EntityId[Literal["token_family"]]):
    """All the refresh tokens rotated out of one login."""

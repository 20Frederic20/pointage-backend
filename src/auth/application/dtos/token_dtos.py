from dataclasses import dataclass

from core.application import DTO


@dataclass(frozen=True)
class TokenPairDTO(DTO):
    """``refresh_token`` is the raw value: returned once, stored only hashed."""

    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"


@dataclass(frozen=True)
class PrincipalDTO(DTO):
    """The authenticated caller, read from a verified access token."""

    user_id: str
    role: str

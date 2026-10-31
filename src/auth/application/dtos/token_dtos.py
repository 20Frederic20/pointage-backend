from dataclasses import dataclass

from core.application import DTO

from .account_dtos import EmploymentDTO


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
    # The employee record the session works with (``None``: an account without one).
    employee_id: str | None = None


@dataclass(frozen=True)
class SelectionRequiredDTO(DTO):
    """Several active companies: the client picks one with ``selection_token``."""

    selection_token: str
    employments: tuple["EmploymentDTO", ...]

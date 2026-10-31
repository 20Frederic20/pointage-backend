"""Open a session on an employee record: the refresh token and the access token."""

from datetime import UTC, datetime

from ...domain.entities import RefreshToken
from ...domain.value_objects import RefreshTokenId
from ..dtos import TokenPairDTO
from .employment_resolver import BoundSession


async def start_session(tokens, accounts, *, user_id: str, bound: BoundSession) -> tuple[TokenPairDTO, RefreshToken]:
    raw_refresh_token = tokens.new_refresh_token()
    refresh_token = RefreshToken.start_session(
        RefreshTokenId.generate(),
        user_id=user_id,
        token_hash=tokens.hash_refresh_token(raw_refresh_token),
        now=datetime.now(UTC),
        idle_ttl=tokens.refresh_token_idle_ttl,
        max_lifetime=tokens.session_max_lifetime,
        employee_id=bound.employee_id,
    )
    await accounts.record_activity(user_id)
    pair = TokenPairDTO(
        access_token=tokens.issue_access_token(user_id=user_id, role=bound.role, employee_id=bound.employee_id),
        refresh_token=raw_refresh_token,
        expires_in=tokens.access_token_ttl_seconds,
    )
    return pair, refresh_token

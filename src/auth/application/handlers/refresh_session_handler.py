"""Refresh: rotate the refresh token and issue a new access token.

Returns ``None`` when the session is rejected *after* revoking tokens (reuse
of a revoked token, or an account that is no longer active). The revocation
must be committed, so it cannot be an exception raised inside the unit of
work; the router turns ``None`` into ``401 INVALID_REFRESH_TOKEN``.
"""

from collections.abc import Sequence
from datetime import UTC, datetime

from core.application import CommandHandler, IEventOutbox, IUnitOfWork
from core.domain.entity import AggregateRoot

from ...domain.entities import RefreshToken
from ...domain.errors import InvalidRefreshTokenError
from ...domain.repositories import IRefreshTokenRepository
from ...domain.value_objects import RefreshTokenId
from ..commands import RefreshSessionCommand
from ..dtos import TokenPairDTO
from ..ports import TokenIssuer, UserAccounts


class RefreshSessionHandler(CommandHandler[RefreshSessionCommand, TokenPairDTO | None]):
    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        refresh_token_repository: IRefreshTokenRepository,
        user_accounts: UserAccounts,
        token_issuer: TokenIssuer,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._refresh_tokens = refresh_token_repository
        self._accounts = user_accounts
        self._tokens = token_issuer

    async def _execute(
        self, request: RefreshSessionCommand
    ) -> tuple[TokenPairDTO | None, Sequence[AggregateRoot]]:
        now = datetime.now(UTC)
        token = await self._refresh_tokens.find_by_token_hash(
            self._tokens.hash_refresh_token(request.refresh_token)
        )
        if token is None or token.is_expired(now):
            raise InvalidRefreshTokenError("Invalid refresh token")

        if token.is_revoked():
            # A rotated token came back: someone holds a copy. Kill the session.
            family = await self._refresh_tokens.find_active_by_family(token.family_id)
            for member in family:
                member.revoke(now)
            return None, family

        account = await self._accounts.get_account(token.user_id)
        if account is None or not account.is_active:
            token.revoke(now)
            return None, [token]

        raw_refresh_token = self._tokens.new_refresh_token()
        successor = token.rotate(
            successor_id=RefreshTokenId.generate(),
            successor_hash=self._tokens.hash_refresh_token(raw_refresh_token),
            now=now,
            idle_ttl=self._tokens.refresh_token_idle_ttl,
        )
        await self._accounts.record_activity(account.id)
        tokens = TokenPairDTO(
            access_token=self._tokens.issue_access_token(user_id=account.id, role=account.role),
            refresh_token=raw_refresh_token,
            expires_in=self._tokens.access_token_ttl_seconds,
        )
        return tokens, [token, successor]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, RefreshToken):
            await self._refresh_tokens.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")

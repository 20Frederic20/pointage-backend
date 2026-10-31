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
from ..services import BoundSession


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
        bound = await self._bound_record(token, account)
        if bound is None:
            # The record was deactivated, or an unbound session now has a choice to make.
            token.revoke(now)
            return None, [token]

        raw_refresh_token = self._tokens.new_refresh_token()
        successor = token.rotate(
            successor_id=RefreshTokenId.generate(),
            successor_hash=self._tokens.hash_refresh_token(raw_refresh_token),
            now=now,
            idle_ttl=self._tokens.refresh_token_idle_ttl,
            employee_id=bound.employee_id,
        )
        await self._accounts.record_activity(account.id)
        tokens = TokenPairDTO(
            access_token=self._tokens.issue_access_token(
                user_id=account.id, role=bound.role, employee_id=bound.employee_id
            ),
            refresh_token=raw_refresh_token,
            expires_in=self._tokens.access_token_ttl_seconds,
        )
        return tokens, [token, successor]

    async def _bound_record(self, token: RefreshToken, account) -> BoundSession | None:
        """The session's employee record if still active; an unbound session (opened
        before records were bound) binds the single active record, if there is one."""
        employments = await self._accounts.employments(account.id)
        active = [e for e in employments if e.is_active]
        if token.employee_id is not None:
            chosen = next((e for e in active if e.employee_id == token.employee_id), None)
            return BoundSession(chosen.employee_id, chosen.role) if chosen else None
        if not employments:
            return BoundSession(None, account.role)
        return BoundSession(active[0].employee_id, active[0].role) if len(active) == 1 else None

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, RefreshToken):
            await self._refresh_tokens.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")

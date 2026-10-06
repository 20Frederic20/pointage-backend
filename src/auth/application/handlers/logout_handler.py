"""Logout: revoke every token of the session. Idempotent — an unknown token
is a silent no-op, so the endpoint reveals nothing."""

from collections.abc import Sequence
from datetime import UTC, datetime

from core.application import CommandHandler, IEventOutbox, IUnitOfWork
from core.domain.entity import AggregateRoot

from ...domain.entities import RefreshToken
from ...domain.repositories import IRefreshTokenRepository
from ..commands import LogoutCommand
from ..ports import TokenIssuer


class LogoutHandler(CommandHandler[LogoutCommand, None]):
    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        refresh_token_repository: IRefreshTokenRepository,
        token_issuer: TokenIssuer,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._refresh_tokens = refresh_token_repository
        self._tokens = token_issuer

    async def _execute(self, request: LogoutCommand) -> tuple[None, Sequence[AggregateRoot]]:
        token = await self._refresh_tokens.find_by_token_hash(
            self._tokens.hash_refresh_token(request.refresh_token)
        )
        if token is None:
            return None, []
        now = datetime.now(UTC)
        family = await self._refresh_tokens.find_active_by_family(token.family_id)
        for member in family:
            member.revoke(now)
        return None, family

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, RefreshToken):
            await self._refresh_tokens.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")

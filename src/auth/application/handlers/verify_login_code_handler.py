"""Verify a login code: on a match, open a session like a password login.

Returns ``None`` on a wrong code *after* counting the attempt. The count
must be committed — an exception would roll it back and allow unlimited
guessing — so the router turns ``None`` into ``401 INVALID_LOGIN_CODE``.
"""

from collections.abc import Sequence
from datetime import UTC, datetime

from core.application import CommandHandler, IEventOutbox, IUnitOfWork
from core.audit import audit
from core.domain.entity import AggregateRoot

from ...domain.entities import LoginCode, RefreshToken
from ...domain.errors import InvalidLoginCodeError
from ...domain.repositories import ILoginCodeRepository, IRefreshTokenRepository
from ...domain.value_objects import RefreshTokenId
from ..commands import VerifyLoginCodeCommand
from ..dtos import TokenPairDTO
from ..ports import TokenIssuer, UserAccounts


class VerifyLoginCodeHandler(CommandHandler[VerifyLoginCodeCommand, TokenPairDTO | None]):
    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        login_code_repository: ILoginCodeRepository,
        refresh_token_repository: IRefreshTokenRepository,
        user_accounts: UserAccounts,
        token_issuer: TokenIssuer,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._login_codes = login_code_repository
        self._refresh_tokens = refresh_token_repository
        self._accounts = user_accounts
        self._tokens = token_issuer

    async def _execute(
        self, request: VerifyLoginCodeCommand
    ) -> tuple[TokenPairDTO | None, Sequence[AggregateRoot]]:
        account = await self._accounts.find_credentials(request.identifier)
        if account is None or not account.is_active or account.password_hash is not None:
            raise InvalidLoginCodeError("Invalid login code")
        login_code = await self._login_codes.find_latest_for_user(account.id)
        if login_code is None:
            raise InvalidLoginCodeError("Invalid login code")

        now = datetime.now(UTC)
        code_hash = self._tokens.hash_login_code(user_id=account.id, code=request.code)
        if not login_code.verify(code_hash, now):
            audit.warning("action=OTP_VERIFY identifier=%s status=FAIL reason=invalid_code", request.identifier)
            return None, [login_code]

        raw_refresh_token = self._tokens.new_refresh_token()
        refresh_token = RefreshToken.start_session(
            RefreshTokenId.generate(),
            user_id=account.id,
            token_hash=self._tokens.hash_refresh_token(raw_refresh_token),
            now=now,
            idle_ttl=self._tokens.refresh_token_idle_ttl,
            max_lifetime=self._tokens.session_max_lifetime,
        )
        await self._accounts.record_activity(account.id)
        tokens = TokenPairDTO(
            access_token=self._tokens.issue_access_token(user_id=account.id, role=account.role),
            refresh_token=raw_refresh_token,
            expires_in=self._tokens.access_token_ttl_seconds,
        )
        audit.info("action=OTP_VERIFY identifier=%s user_id=%s status=OK", request.identifier, account.id)
        return tokens, [login_code, refresh_token]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, LoginCode):
            await self._login_codes.save(aggregate)
        elif isinstance(aggregate, RefreshToken):
            await self._refresh_tokens.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")

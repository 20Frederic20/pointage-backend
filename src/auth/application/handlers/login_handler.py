"""Login: verify the password, then issue an access token and a refresh token."""

from collections.abc import Sequence
from datetime import UTC, datetime

from core.application import CommandHandler, IEventOutbox, IUnitOfWork
from core.domain.entity import AggregateRoot
from identity.application.ports import PasswordHasher

from ...domain.entities import RefreshToken
from ...domain.errors import InvalidCredentialsError
from ...domain.repositories import IRefreshTokenRepository
from ...domain.value_objects import RefreshTokenId
from ..commands import LoginCommand
from ..dtos import TokenPairDTO
from ..ports import TokenIssuer, UserAccounts


class LoginHandler(CommandHandler[LoginCommand, TokenPairDTO]):
    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        refresh_token_repository: IRefreshTokenRepository,
        user_accounts: UserAccounts,
        password_hasher: PasswordHasher,
        token_issuer: TokenIssuer,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._refresh_tokens = refresh_token_repository
        self._accounts = user_accounts
        self._passwords = password_hasher
        self._tokens = token_issuer

    async def _execute(self, request: LoginCommand) -> tuple[TokenPairDTO, Sequence[AggregateRoot]]:
        account = await self._accounts.find_credentials(request.email)
        # Exactly one verify on every path — unknown email and code-only
        # account included — so the response time does not reveal which
        # accounts exist or which ones have a password.
        has_password = account is not None and account.password_hash is not None
        hashed = account.password_hash if has_password else self._passwords.dummy_hash
        password_ok = self._passwords.verify(request.password, hashed)
        if not has_password or not password_ok or not account.is_active:
            raise InvalidCredentialsError("Invalid email or password")

        raw_refresh_token = self._tokens.new_refresh_token()
        refresh_token = RefreshToken.start_session(
            RefreshTokenId.generate(),
            user_id=account.id,
            token_hash=self._tokens.hash_refresh_token(raw_refresh_token),
            now=datetime.now(UTC),
            idle_ttl=self._tokens.refresh_token_idle_ttl,
            max_lifetime=self._tokens.session_max_lifetime,
        )
        await self._accounts.record_activity(account.id)
        tokens = TokenPairDTO(
            access_token=self._tokens.issue_access_token(user_id=account.id, role=account.role),
            refresh_token=raw_refresh_token,
            expires_in=self._tokens.access_token_ttl_seconds,
        )
        return tokens, [refresh_token]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, RefreshToken):
            await self._refresh_tokens.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")

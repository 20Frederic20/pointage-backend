"""Login: verify the password, then issue an access token and a refresh token."""

from collections.abc import Sequence

from core.application import CommandHandler, IEventOutbox, IUnitOfWork
from core.audit import audit
from core.domain.entity import AggregateRoot
from identity.application.ports import PasswordHasher

from ...domain.entities import RefreshToken
from ...domain.errors import InvalidCredentialsError
from ...domain.repositories import IRefreshTokenRepository
from ..commands import LoginCommand
from ..dtos import SelectionRequiredDTO, TokenPairDTO
from ..ports import TokenIssuer, UserAccounts
from ..services import SelectionRequired, resolve_employment, start_session


class LoginHandler(CommandHandler[LoginCommand, TokenPairDTO | SelectionRequiredDTO]):
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

    async def _execute(
        self, request: LoginCommand
    ) -> tuple[TokenPairDTO | SelectionRequiredDTO, Sequence[AggregateRoot]]:
        account = await self._accounts.find_credentials(request.identifier)
        # Exactly one verify on every path — unknown identifier and code-only
        # account included — so the response time does not reveal which
        # accounts exist or which ones have a password.
        has_password = account is not None and account.password_hash is not None
        hashed = account.password_hash if has_password else self._passwords.dummy_hash
        password_ok = self._passwords.verify(request.password, hashed)
        if not has_password or not password_ok or not account.is_active:
            audit.warning("action=LOGIN_PASSWORD identifier=%s status=FAIL", request.identifier)
            raise InvalidCredentialsError("Invalid identifier or password")

        outcome = resolve_employment(account, await self._accounts.employments(account.id))
        if outcome is None:
            audit.warning("action=LOGIN_PASSWORD identifier=%s status=FAIL reason=inactive_record", request.identifier)
            raise InvalidCredentialsError("Invalid identifier or password")
        if isinstance(outcome, SelectionRequired):
            audit.info("action=LOGIN_PASSWORD identifier=%s user_id=%s status=CHOICE", request.identifier, account.id)
            return SelectionRequiredDTO(
                selection_token=self._tokens.issue_selection_token(user_id=account.id),
                employments=outcome.employments,
            ), []
        tokens, refresh_token = await start_session(self._tokens, self._accounts, user_id=account.id, bound=outcome)
        audit.info("action=LOGIN_PASSWORD identifier=%s user_id=%s status=OK", request.identifier, account.id)
        return tokens, [refresh_token]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, RefreshToken):
            await self._refresh_tokens.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")

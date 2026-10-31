"""Several active companies: open the session on the employee record the user chose."""

from collections.abc import Sequence

from core.application import CommandHandler, IEventOutbox, IUnitOfWork
from core.audit import audit
from core.domain.entity import AggregateRoot

from ...domain.entities import RefreshToken
from ...domain.errors import NoActiveEmploymentError
from ...domain.repositories import IRefreshTokenRepository
from ..commands import SelectEmployeeCommand
from ..dtos import TokenPairDTO
from ..ports import TokenIssuer, UserAccounts
from ..services import BoundSession, start_session


class SelectEmployeeHandler(CommandHandler[SelectEmployeeCommand, TokenPairDTO]):
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

    async def _execute(self, request: SelectEmployeeCommand) -> tuple[TokenPairDTO, Sequence[AggregateRoot]]:
        user_id = self._tokens.decode_selection_token(request.selection_token)
        account = await self._accounts.get_account(user_id)
        employments = await self._accounts.employments(user_id) if account and account.is_active else []
        chosen = next((e for e in employments if e.employee_id == request.employee_id and e.is_active), None)
        if chosen is None:
            audit.warning("action=SELECT_EMPLOYEE user_id=%s employee=%s status=FAIL", user_id, request.employee_id)
            raise NoActiveEmploymentError("Not an active employee record of this account", context=request.employee_id)
        tokens, refresh_token = await start_session(
            self._tokens, self._accounts, user_id=user_id, bound=BoundSession(chosen.employee_id, chosen.role)
        )
        audit.info("action=SELECT_EMPLOYEE user_id=%s employee=%s status=OK", user_id, chosen.employee_id)
        return tokens, [refresh_token]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, RefreshToken):
            await self._refresh_tokens.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")

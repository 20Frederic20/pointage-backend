"""Request a login code: store it hashed, return the email to send.

The handler does not send the email itself: the router delivers it in the
background once the response is out, so the SMTP round trip never reveals
that the account exists. Every refusal is silent (``None``) for the same
reason.
"""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from core.application import CommandHandler, IEventOutbox, IUnitOfWork
from core.domain.entity import AggregateRoot

from ...domain.entities import LoginCode
from ...domain.repositories import ILoginCodeRepository
from ...domain.value_objects import LoginCodeId
from ..commands import RequestLoginCodeCommand
from ..dtos import OutgoingEmailDTO
from ..ports import TokenIssuer, UserAccounts

# Anti-flooding: one code per minute, five per hour, per account. With
# ``LoginCode.MAX_ATTEMPTS`` that caps guessing at 25 tries an hour.
RESEND_COOLDOWN = timedelta(seconds=60)
MAX_CODES_PER_HOUR = 5


class RequestLoginCodeHandler(CommandHandler[RequestLoginCodeCommand, OutgoingEmailDTO | None]):
    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        login_code_repository: ILoginCodeRepository,
        user_accounts: UserAccounts,
        token_issuer: TokenIssuer,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._login_codes = login_code_repository
        self._accounts = user_accounts
        self._tokens = token_issuer

    async def _execute(
        self, request: RequestLoginCodeCommand
    ) -> tuple[OutgoingEmailDTO | None, Sequence[AggregateRoot]]:
        account = await self._accounts.find_credentials(request.email)
        if account is None or not account.is_active or account.password_hash is not None:
            return None, []

        now = datetime.now(UTC)
        latest = await self._login_codes.find_latest_for_user(account.id)
        if latest is not None and now - latest.created_at < RESEND_COOLDOWN:
            return None, []
        if await self._login_codes.count_issued_since(account.id, now - timedelta(hours=1)) >= MAX_CODES_PER_HOUR:
            return None, []

        code = self._tokens.new_login_code()
        login_code = LoginCode.issue(
            LoginCodeId.generate(),
            user_id=account.id,
            code_hash=self._tokens.hash_login_code(user_id=account.id, code=code),
            now=now,
        )
        minutes = int(LoginCode.TTL.total_seconds() // 60)
        email = OutgoingEmailDTO(
            to=request.email,
            # Code kept out of the subject: it would show on locked screens.
            subject="Your Pointage login code",
            body=(
                f"Your Pointage login code is {code}.\n\n"
                f"It is valid for {minutes} minutes and can be used once.\n"
                "If you did not ask for it, ignore this email."
            ),
        )
        return email, [login_code]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, LoginCode):
            await self._login_codes.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")

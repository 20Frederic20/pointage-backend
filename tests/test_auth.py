"""The auth security rules, one test each, against in-memory fakes.

No database: handlers run through the real ``CommandHandler`` template with a
no-op unit of work; tokens go through the real ``JwtTokenIssuer``.
Run from ``backend/``: ``uv run pytest``.
"""

import asyncio
import re
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from auth.application.commands import (
    LoginCommand,
    LogoutCommand,
    RefreshSessionCommand,
    RequestLoginCodeCommand,
    VerifyLoginCodeCommand,
)
from auth.application.dtos import AccountCredentialsDTO, AccountDTO
from auth.application.handlers import (
    LoginHandler,
    LogoutHandler,
    RefreshSessionHandler,
    RequestLoginCodeHandler,
    VerifyLoginCodeHandler,
)
from auth.application.ports import UserAccounts
from auth.domain.entities import LoginCode, RefreshToken
from auth.domain.errors import (
    InvalidAccessTokenError,
    InvalidCredentialsError,
    InvalidLoginCodeError,
    InvalidRefreshTokenError,
)
from auth.domain.repositories import ILoginCodeRepository, IRefreshTokenRepository
from auth.domain.value_objects import RefreshTokenId
from auth.infrastructure import JwtTokenIssuer
from auth.interface import require_role
from auth.interface.routers import auth_router
from core.exceptions import register_exception_handlers
from core.settings import AuthSettings
from identity.application.commands import ClearUserPasswordCommand, RegisterUserCommand
from identity.application.handlers import ClearUserPasswordHandler, RegisterUserHandler
from identity.application.ports import PasswordHasher
from identity.domain.errors import RegistrationClosedError, RolePermissionDeniedError
from identity.domain.repositories import IUserRepository


def run(coro):
    return asyncio.run(coro)


# ---- fakes ------------------------------------------------------------------


class NoopUnitOfWork:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return None

    async def commit(self):
        pass

    async def rollback(self):
        pass


class FakePasswordHasher(PasswordHasher):
    def __init__(self):
        self.verify_calls = 0

    def hash(self, plain):
        return f"hashed:{plain}"

    def verify(self, plain, hashed):
        self.verify_calls += 1
        return hashed == f"hashed:{plain}"

    @property
    def dummy_hash(self):
        return "hashed:dummy"


class FakeUserAccounts(UserAccounts):
    def __init__(self):
        self.accounts = {}  # email -> AccountCredentialsDTO

    def add(self, email, password, *, role="EMPLOYEE", is_active=True, user_id="usr1"):
        """``password=None``: a code-only account."""
        self.accounts[email] = AccountCredentialsDTO(
            id=user_id,
            role=role,
            is_active=is_active,
            password_hash=f"hashed:{password}" if password is not None else None,
        )

    async def find_credentials(self, email):
        return self.accounts.get(email)

    async def get_account(self, user_id):
        for a in self.accounts.values():
            if a.id == user_id:
                return AccountDTO(id=a.id, role=a.role, is_active=a.is_active)
        return None

    async def record_activity(self, user_id):
        pass


class FakeRefreshTokenRepository(IRefreshTokenRepository):
    def __init__(self):
        self.rows = {}

    async def get_by_id(self, token_id):
        return self.rows[token_id.value]

    async def exists(self, token_id):
        return token_id.value in self.rows

    async def save(self, token):
        self.rows[token.id.value] = token
        token._advance_version()

    async def delete(self, token_id):
        self.rows.pop(token_id.value, None)

    async def find_by_token_hash(self, token_hash):
        return next((t for t in self.rows.values() if t.token_hash == token_hash), None)

    async def find_active_by_family(self, family_id):
        return [t for t in self.rows.values() if t.family_id == family_id and not t.is_revoked()]


class FakeLoginCodeRepository(ILoginCodeRepository):
    def __init__(self):
        self.rows = {}

    async def get_by_id(self, code_id):
        return self.rows[code_id.value]

    async def exists(self, code_id):
        return code_id.value in self.rows

    async def save(self, code):
        self.rows[code.id.value] = code
        code._advance_version()

    async def delete(self, code_id):
        self.rows.pop(code_id.value, None)

    async def find_latest_for_user(self, user_id):
        mine = [c for c in self.rows.values() if c.user_id == user_id]
        return max(mine, key=lambda c: c.created_at, default=None)

    async def count_issued_since(self, user_id, since):
        return sum(1 for c in self.rows.values() if c.user_id == user_id and c.created_at >= since)


def make_issuer(**overrides):
    return JwtTokenIssuer(AuthSettings(jwt_secret="test-secret-" + "x" * 32, **overrides))


@pytest.fixture
def env():
    accounts = FakeUserAccounts()
    accounts.add("ana@pointage.test", "correct-password")
    tokens = make_issuer()
    accounts.add("kofi@pointage.bj", None, user_id="usr3")  # code-only account
    repo = FakeRefreshTokenRepository()
    codes = FakeLoginCodeRepository()
    hasher = FakePasswordHasher()
    common = dict(unit_of_work=NoopUnitOfWork(), refresh_token_repository=repo)
    return SimpleNamespace(
        accounts=accounts,
        tokens=tokens,
        repo=repo,
        codes=codes,
        hasher=hasher,
        request_code=lambda email: run(
            RequestLoginCodeHandler(
                unit_of_work=NoopUnitOfWork(), login_code_repository=codes, user_accounts=accounts, token_issuer=tokens
            ).handle(RequestLoginCodeCommand(email=email))
        ),
        verify_code=lambda email, code: run(
            VerifyLoginCodeHandler(**common, login_code_repository=codes, user_accounts=accounts, token_issuer=tokens).handle(
                VerifyLoginCodeCommand(email=email, code=code)
            )
        ),
        login=lambda email, pw: run(
            LoginHandler(**common, user_accounts=accounts, password_hasher=hasher, token_issuer=tokens).handle(
                LoginCommand(email=email, password=pw)
            )
        ),
        refresh=lambda raw: run(
            RefreshSessionHandler(**common, user_accounts=accounts, token_issuer=tokens).handle(
                RefreshSessionCommand(refresh_token=raw)
            )
        ),
        logout=lambda raw: run(
            LogoutHandler(**common, token_issuer=tokens).handle(LogoutCommand(refresh_token=raw))
        ),
    )


# ---- login ------------------------------------------------------------------


def test_login_issues_an_access_token_for_the_account(env):
    pair = env.login("ana@pointage.test", "correct-password")
    principal = env.tokens.decode_access_token(pair.access_token)
    assert (principal.user_id, principal.role) == ("usr1", "EMPLOYEE")


def test_unknown_email_and_wrong_password_fail_the_same_way(env):
    with pytest.raises(InvalidCredentialsError) as unknown:
        env.login("nobody@pointage.test", "correct-password")
    with pytest.raises(InvalidCredentialsError) as wrong:
        env.login("ana@pointage.test", "wrong-password")
    assert unknown.value.message == wrong.value.message
    # One argon2 verify on both paths: the timing does not reveal the account.
    assert env.hasher.verify_calls == 2


def test_inactive_account_cannot_log_in(env):
    env.accounts.add("old@pointage.test", "correct-password", is_active=False, user_id="usr2")
    with pytest.raises(InvalidCredentialsError):
        env.login("old@pointage.test", "correct-password")


# ---- refresh ----------------------------------------------------------------


def test_refresh_rotates_and_the_old_token_stops_working(env):
    first = env.login("ana@pointage.test", "correct-password")
    second = env.refresh(first.refresh_token)
    assert second is not None and second.refresh_token != first.refresh_token
    assert env.refresh(second.refresh_token) is not None


def test_reusing_a_rotated_token_revokes_the_whole_session(env):
    first = env.login("ana@pointage.test", "correct-password")
    second = env.refresh(first.refresh_token)
    assert env.refresh(first.refresh_token) is None  # replay of a rotated token
    assert env.refresh(second.refresh_token) is None  # the legitimate one died too
    assert all(t.is_revoked() for t in env.repo.rows.values())


def test_unknown_or_expired_refresh_token_is_rejected(env):
    with pytest.raises(InvalidRefreshTokenError):
        env.refresh("not-a-real-token")
    pair = env.login("ana@pointage.test", "correct-password")
    token = next(iter(env.repo.rows.values()))
    token._expires_at = datetime.now(UTC) - timedelta(seconds=1)
    with pytest.raises(InvalidRefreshTokenError):
        env.refresh(pair.refresh_token)


def test_deactivated_account_cannot_refresh(env):
    pair = env.login("ana@pointage.test", "correct-password")
    env.accounts.add("ana@pointage.test", "correct-password", is_active=False)
    assert env.refresh(pair.refresh_token) is None


def test_logout_revokes_the_session_and_ignores_unknown_tokens(env):
    pair = env.login("ana@pointage.test", "correct-password")
    env.logout(pair.refresh_token)
    env.logout("not-a-real-token")  # no error, nothing revealed
    assert env.refresh(pair.refresh_token) is None


def test_password_login_is_refused_for_a_code_only_account(env):
    with pytest.raises(InvalidCredentialsError):
        env.login("kofi@pointage.bj", "anything")
    assert env.hasher.verify_calls == 1  # same work as a real check: no timing tell


# ---- sliding session -----------------------------------------------------------

T0 = datetime(2026, 10, 9, 18, 0, tzinfo=UTC)  # a Friday, 18:00
IDLE, MAX = timedelta(hours=36), timedelta(days=30)


def new_session(now=T0):
    return RefreshToken.start_session(
        RefreshTokenId.generate(), user_id="usr1", token_hash="h0", now=now, idle_ttl=IDLE, max_lifetime=MAX
    )


def rotate(token, now):
    return token.rotate(successor_id=RefreshTokenId.generate(), successor_hash=f"h{now}", now=now, idle_ttl=IDLE)


def test_evening_to_next_morning_keeps_the_session():
    token = new_session(T0 - timedelta(days=1))  # Thursday 18:00
    next_morning = T0 - timedelta(days=1) + timedelta(hours=14)  # Friday 08:00
    assert token.is_usable(next_morning)
    assert rotate(token, next_morning).expires_at == next_morning + IDLE


def test_weekend_kills_the_session():
    token = new_session()  # Friday 18:00
    monday_morning = T0 + timedelta(days=2, hours=14)  # Monday 08:00, 62 h later
    assert not token.is_usable(monday_morning)


def test_daily_activity_never_extends_a_session_past_30_days():
    token = new_session()
    now = T0
    for _ in range(29):
        now += timedelta(days=1)
        token = rotate(token, now)
    assert token.expires_at == T0 + MAX  # capped, not now + 36 h
    assert not token.is_usable(T0 + MAX)


# ---- login by emailed code ------------------------------------------------------


def code_in(email):
    return re.search(r"\b(\d{6})\b", email.body).group(1)


def test_code_is_emailed_only_to_active_code_only_accounts(env):
    env.accounts.add("gone@pointage.bj", None, user_id="usr4", is_active=False)
    email = env.request_code("kofi@pointage.bj")
    assert email.to == "kofi@pointage.bj" and len(code_in(email)) == 6
    for silent in ("nobody@pointage.bj", "ana@pointage.test", "gone@pointage.bj"):
        assert env.request_code(silent) is None  # same 202 for the caller
    assert all(c.code_hash != code_in(email) for c in env.codes.rows.values())  # stored hashed


def test_right_code_logs_in_once(env):
    code = code_in(env.request_code("kofi@pointage.bj"))
    pair = env.verify_code("kofi@pointage.bj", code)
    assert env.tokens.decode_access_token(pair.access_token).user_id == "usr3"
    assert env.verify_code("kofi@pointage.bj", code) is None  # single use


def test_wrong_codes_are_counted_and_the_fifth_kills_the_code(env):
    code = code_in(env.request_code("kofi@pointage.bj"))
    wrong = "000000" if code != "000000" else "111111"
    for attempt in range(1, LoginCode.MAX_ATTEMPTS + 1):
        assert env.verify_code("kofi@pointage.bj", wrong) is None
        assert next(iter(env.codes.rows.values())).attempts == attempt  # persisted, not rolled back
    assert env.verify_code("kofi@pointage.bj", code) is None


def test_expired_code_is_refused(env):
    code = code_in(env.request_code("kofi@pointage.bj"))
    next(iter(env.codes.rows.values()))._expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert env.verify_code("kofi@pointage.bj", code) is None


def test_unknown_email_or_password_account_cannot_verify_a_code(env):
    with pytest.raises(InvalidLoginCodeError):
        env.verify_code("nobody@pointage.bj", "123456")
    with pytest.raises(InvalidLoginCodeError):
        env.verify_code("ana@pointage.test", "123456")


def test_resend_cooldown_hourly_cap_and_only_the_latest_code_counts(env):
    first = code_in(env.request_code("kofi@pointage.bj"))
    assert env.request_code("kofi@pointage.bj") is None  # within 60 s

    def age_codes(by):
        for c in env.codes.rows.values():
            c._created_at -= by

    age_codes(timedelta(minutes=2))
    second = code_in(env.request_code("kofi@pointage.bj"))
    if first != second:
        assert env.verify_code("kofi@pointage.bj", first) is None  # superseded
    for _ in range(3):
        age_codes(timedelta(minutes=2))
        assert env.request_code("kofi@pointage.bj") is not None
    age_codes(timedelta(minutes=2))
    assert env.request_code("kofi@pointage.bj") is None  # 5 codes this hour


# ---- access tokens and guards ------------------------------------------------


def test_expired_or_forged_access_token_is_rejected():
    expired = make_issuer(access_token_ttl_seconds=-1).issue_access_token(user_id="usr1", role="ADMIN")
    with pytest.raises(InvalidAccessTokenError):
        make_issuer().decode_access_token(expired)
    forged = JwtTokenIssuer(AuthSettings(jwt_secret="other-secret-" + "y" * 32)).issue_access_token(
        user_id="usr1", role="ADMIN"
    )
    with pytest.raises(InvalidAccessTokenError):
        make_issuer().decode_access_token(forged)


def test_guards_return_401_without_token_and_403_for_the_wrong_role():
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(auth_router)
    tokens = make_issuer()
    app.state.container = SimpleNamespace(token_issuer=tokens)

    @app.get("/hr-only")
    def hr_only(principal=Depends(require_role("HR", "ADMIN"))):
        return {"userId": principal.user_id}

    client = TestClient(app)
    employee = {"Authorization": "Bearer " + tokens.issue_access_token(user_id="usr1", role="EMPLOYEE")}
    hr = {"Authorization": "Bearer " + tokens.issue_access_token(user_id="usr2", role="HR")}

    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
    assert client.get("/auth/me", headers=employee).json() == {"userId": "usr1", "role": "EMPLOYEE"}
    assert client.get("/hr-only", headers=employee).status_code == 403
    assert client.get("/hr-only", headers=hr).json() == {"userId": "usr2"}


# ---- registration (identity) -------------------------------------------------


class FakeUserRepository(IUserRepository):
    def __init__(self):
        self.users = []

    async def get_by_id(self, user_id):
        return next(u for u in self.users if u.id == user_id)

    async def save(self, user):
        if user not in self.users:
            self.users.append(user)
        user._advance_version()

    async def delete(self, user_id):
        raise NotImplementedError

    async def exists(self, user_id):
        raise NotImplementedError

    async def find_by_email(self, email):
        return next((u for u in self.users if u.email == email.strip().lower()), None)

    async def exists_any(self):
        return bool(self.users)

    async def find(self, spec, *, limit=50, offset=0):
        raise NotImplementedError

    async def count_active(self):
        raise NotImplementedError

    async def count(self, spec):
        raise NotImplementedError


def test_first_account_is_admin_then_only_an_admin_creates_accounts():
    repo = FakeUserRepository()

    def register(email, **kw):
        handler = RegisterUserHandler(
            unit_of_work=NoopUnitOfWork(), user_repository=repo, password_hasher=FakePasswordHasher()
        )
        return run(handler.handle(RegisterUserCommand(email=email, password="password123", **kw)))

    founder = register("boss@pointage.test", role="EMPLOYEE")
    assert founder.role == "ADMIN"  # bootstrap ignores the requested role

    with pytest.raises(RegistrationClosedError):
        register("intruder@pointage.test")
    with pytest.raises(RegistrationClosedError):
        register("intruder@pointage.test", requested_by_role="HR")

    created = register("ana@pointage.test", role="MANAGER", requested_by_role="ADMIN")
    assert created.role == "MANAGER"


def test_account_without_password_and_admin_only_password_removal():
    repo = FakeUserRepository()

    def send(handler_cls, command, **deps):
        return run(handler_cls(unit_of_work=NoopUnitOfWork(), user_repository=repo, **deps).handle(command))

    hasher = FakePasswordHasher()
    admin = send(RegisterUserHandler, RegisterUserCommand(email="boss@pointage.bj", password="password123"), password_hasher=hasher)
    kofi = send(
        RegisterUserHandler,
        RegisterUserCommand(email="kofi@pointage.bj", requested_by_role="ADMIN"),
        password_hasher=hasher,
    )
    ana = send(
        RegisterUserHandler,
        RegisterUserCommand(email="ana@pointage.bj", password="password123", requested_by_role="ADMIN"),
        password_hasher=hasher,
    )
    by_email = {u.email: u for u in repo.users}
    assert by_email["kofi@pointage.bj"].password_hash is None
    assert by_email["ana@pointage.bj"].password_hash is not None

    with pytest.raises(RolePermissionDeniedError):
        send(ClearUserPasswordHandler, ClearUserPasswordCommand(user_id=admin.id, actor_id=kofi.id))
    send(ClearUserPasswordHandler, ClearUserPasswordCommand(user_id=ana.id, actor_id=admin.id))
    assert by_email["ana@pointage.bj"].password_hash is None

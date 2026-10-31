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
    SelectEmployeeCommand,
    LoginCommand,
    LogoutCommand,
    RefreshSessionCommand,
    RequestLoginCodeCommand,
    VerifyLoginCodeCommand,
)
from auth.application.dtos import AccountCredentialsDTO, AccountDTO
from auth.application.handlers import (
    SelectEmployeeHandler,
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
        self.employee_numbers = {}  # employee number -> email
        self.records = {}  # user id -> [EmploymentDTO]
        self.record_numbers = {}  # employee number -> employee id

    def add_employment(self, user_id, employee_id, *, company="Société A", role="EMPLOYEE", active=True, number=None):
        from auth.application.dtos import EmploymentDTO

        mine = [e for e in self.records.get(user_id, []) if e.employee_id != employee_id]
        mine.append(EmploymentDTO(employee_id=employee_id, company_name=company, role=role, is_active=active))
        self.records[user_id] = mine
        if number is not None:
            self.record_numbers[number] = employee_id

    async def employments(self, user_id):
        return list(self.records.get(user_id, []))

    def add(self, email, password, *, role="EMPLOYEE", is_active=True, user_id="usr1", employee_number=None):
        """``password=None``: a code-only account."""
        self.accounts[email] = AccountCredentialsDTO(
            id=user_id,
            email=email,
            role=role,
            is_active=is_active,
            password_hash=f"hashed:{password}" if password is not None else None,
        )
        if employee_number is not None:
            self.employee_numbers[employee_number] = email

    async def find_credentials(self, identifier):
        from dataclasses import replace

        email = identifier if "@" in identifier else self.employee_numbers.get(identifier)
        account = self.accounts.get(email)
        if account is not None and "@" not in identifier:
            account = replace(account, employee_id=self.record_numbers.get(identifier))
        return account

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
    accounts.add("ana@pointage.test", "correct-password", employee_number="EMP-001")
    tokens = make_issuer()
    accounts.add("kofi@pointage.bj", None, user_id="usr3", employee_number="EMP-003")  # code-only account
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
        request_code=lambda identifier: run(
            RequestLoginCodeHandler(
                unit_of_work=NoopUnitOfWork(), login_code_repository=codes, user_accounts=accounts, token_issuer=tokens
            ).handle(RequestLoginCodeCommand(identifier=identifier))
        ),
        verify_code=lambda identifier, code: run(
            VerifyLoginCodeHandler(**common, login_code_repository=codes, user_accounts=accounts, token_issuer=tokens).handle(
                VerifyLoginCodeCommand(identifier=identifier, code=code)
            )
        ),
        login=lambda identifier, pw: run(
            LoginHandler(**common, user_accounts=accounts, password_hasher=hasher, token_issuer=tokens).handle(
                LoginCommand(identifier=identifier, password=pw)
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
        select=lambda selection_token, employee_id: run(
            SelectEmployeeHandler(**common, user_accounts=accounts, token_issuer=tokens).handle(
                SelectEmployeeCommand(selection_token=selection_token, employee_id=employee_id)
            )
        ),
    )


# ---- login ------------------------------------------------------------------


def test_login_issues_an_access_token_for_the_account(env):
    pair = env.login("ana@pointage.test", "correct-password")
    principal = env.tokens.decode_access_token(pair.access_token)
    assert (principal.user_id, principal.role) == ("usr1", "EMPLOYEE")


def test_login_by_employee_number_opens_the_same_account(env):
    pair = env.login("EMP-001", "correct-password")
    assert env.tokens.decode_access_token(pair.access_token).user_id == "usr1"
    with pytest.raises(InvalidCredentialsError):
        env.login("EMP-999", "correct-password")  # unknown number: same refusal


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


# ---- employee records: one session per company ------------------------------


def _claims(env, pair):
    return env.tokens.decode_access_token(pair.access_token)


def test_login_by_matricule_binds_that_record(env):
    env.accounts.add_employment("usr1", "emp1", role="MANAGER", number="EMP-001")
    env.accounts.add_employment("usr1", "emp2", role="HR", company="Société B")
    principal = _claims(env, env.login("EMP-001", "correct-password"))
    assert (principal.employee_id, principal.role) == ("emp1", "MANAGER")


def test_login_by_matricule_of_inactive_record_is_invalid_credentials(env):
    env.accounts.add_employment("usr1", "emp1", active=False, number="EMP-001")
    env.accounts.add_employment("usr1", "emp2", company="Société B")
    with pytest.raises(InvalidCredentialsError):
        env.login("EMP-001", "correct-password")


def test_login_by_email_single_active_record_returns_tokens(env):
    env.accounts.add_employment("usr1", "emp1", role="HR")
    principal = _claims(env, env.login("ana@pointage.test", "correct-password"))
    assert (principal.employee_id, principal.role) == ("emp1", "HR")


def test_login_by_email_two_active_records_requires_selection_then_select_issues_bound_token(env):
    from auth.application.dtos import SelectionRequiredDTO

    env.accounts.add_employment("usr1", "emp1", role="EMPLOYEE", company="Société A")
    env.accounts.add_employment("usr1", "emp2", role="MANAGER", company="Société B")
    choice = env.login("ana@pointage.test", "correct-password")
    assert isinstance(choice, SelectionRequiredDTO)
    assert [(e.employee_id, e.company_name, e.role) for e in choice.employments] == [
        ("emp1", "Société A", "EMPLOYEE"), ("emp2", "Société B", "MANAGER")]
    assert env.repo.rows == {}  # no session before the choice
    principal = _claims(env, env.select(choice.selection_token, "emp2"))
    assert (principal.employee_id, principal.role) == ("emp2", "MANAGER")


def test_deactivated_in_one_company_logs_straight_into_the_other(env):
    env.accounts.add_employment("usr1", "emp1", active=False)
    env.accounts.add_employment("usr1", "emp2", role="HR", company="Société B")
    assert _claims(env, env.login("ana@pointage.test", "correct-password")).employee_id == "emp2"


def test_all_records_inactive_is_no_active_employment(env):
    from auth.domain.errors import NoActiveEmploymentError

    env.accounts.add_employment("usr1", "emp1", active=False)
    with pytest.raises(NoActiveEmploymentError):
        env.login("ana@pointage.test", "correct-password")
    assert (NoActiveEmploymentError.code, NoActiveEmploymentError.http_status) == ("NO_ACTIVE_EMPLOYMENT", 403)


def test_account_without_records_keeps_user_role(env):
    principal = _claims(env, env.login("ana@pointage.test", "correct-password"))
    assert (principal.employee_id, principal.role) == (None, "EMPLOYEE")


def test_selection_token_expired_or_forged_is_401(env):
    env.accounts.add_employment("usr1", "emp1")
    env.accounts.add_employment("usr1", "emp2", company="Société B")
    with pytest.raises(InvalidAccessTokenError):
        env.select("forged.token.value", "emp1")
    access = env.login("ana@pointage.test", "correct-password")  # still a selection: no access token
    with pytest.raises(InvalidAccessTokenError):
        env.select(env.tokens.issue_access_token(user_id="usr1", role="EMPLOYEE", employee_id=None), "emp1")
    expired = make_issuer(selection_token_ttl_seconds=-1).issue_selection_token(user_id="usr1")
    with pytest.raises(InvalidAccessTokenError):
        env.select(expired, "emp1")
    assert access.selection_token


def test_select_employee_not_owned_or_inactive_is_403(env):
    from auth.domain.errors import NoActiveEmploymentError

    env.accounts.add_employment("usr1", "emp1")
    env.accounts.add_employment("usr1", "emp2", active=False, company="Société B")
    token = env.tokens.issue_selection_token(user_id="usr1")
    for employee_id in ("emp2", "emp9"):
        with pytest.raises(NoActiveEmploymentError):
            env.select(token, employee_id)


def test_refresh_after_deactivation_is_401(env):
    env.accounts.add_employment("usr1", "emp1")
    pair = env.login("ana@pointage.test", "correct-password")
    env.accounts.add_employment("usr1", "emp1", active=False)
    assert env.refresh(pair.refresh_token) is None


def test_refresh_keeps_the_record_and_its_role(env):
    env.accounts.add_employment("usr1", "emp1", role="EMPLOYEE")
    env.accounts.add_employment("usr1", "emp2", role="HR", company="Société B")
    choice = env.login("ana@pointage.test", "correct-password")
    pair = env.refresh(env.select(choice.selection_token, "emp2").refresh_token)
    assert (_claims(env, pair).employee_id, _claims(env, pair).role) == ("emp2", "HR")


def _legacy_session(env):
    pair = env.login("ana@pointage.test", "correct-password")  # no records yet: unbound session
    assert _claims(env, pair).employee_id is None
    return pair


def test_legacy_refresh_without_employee_binds_single_active_record(env):
    pair = _legacy_session(env)
    env.accounts.add_employment("usr1", "emp1", role="HR")
    assert _claims(env, env.refresh(pair.refresh_token)).employee_id == "emp1"


def test_legacy_refresh_with_two_active_records_is_401(env):
    pair = _legacy_session(env)
    env.accounts.add_employment("usr1", "emp1")
    env.accounts.add_employment("usr1", "emp2", company="Société B")
    assert env.refresh(pair.refresh_token) is None


def test_otp_login_follows_same_selection_rules(env):
    from auth.application.dtos import SelectionRequiredDTO

    env.accounts.add_employment("usr3", "emp7", number="EMP-003")
    env.accounts.add_employment("usr3", "emp8", company="Société B")
    code = code_in(env.request_code("kofi@pointage.bj"))
    assert isinstance(env.verify_code("kofi@pointage.bj", code), SelectionRequiredDTO)


def test_otp_login_by_matricule_binds_that_record(env):
    env.accounts.add_employment("usr3", "emp7", number="EMP-003")
    env.accounts.add_employment("usr3", "emp8", company="Société B")
    code = code_in(env.request_code("EMP-003"))
    assert _claims(env, env.verify_code("EMP-003", code)).employee_id == "emp7"


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


def test_code_requested_by_employee_number_goes_to_the_account_email(env):
    email = env.request_code("EMP-003")
    assert email.to == "kofi@pointage.bj"
    pair = env.verify_code("EMP-003", code_in(email))
    assert env.tokens.decode_access_token(pair.access_token).user_id == "usr3"
    assert env.request_code("EMP-999") is None  # unknown number: same 202


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
    assert client.get("/auth/me", headers=employee).json() == {"employeeId": None, "userId": "usr1", "role": "EMPLOYEE"}
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


def test_login_routes_return_the_company_choice_then_select_employee_tokens(env):
    from auth.infrastructure import AuthContainer
    from auth.interface import get_auth

    env.accounts.add_employment("usr1", "emp1", company="Société A")
    env.accounts.add_employment("usr1", "emp2", role="HR", company="Société B")
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(auth_router)
    app.state.container = SimpleNamespace(token_issuer=env.tokens)
    app.dependency_overrides[get_auth] = lambda: AuthContainer(
        refresh_token_repository=env.repo, login_code_repository=env.codes, unit_of_work=NoopUnitOfWork(),
        event_bus=SimpleNamespace(publish=lambda event: None), user_accounts=env.accounts,
        password_hasher=env.hasher, token_issuer=env.tokens)
    client = TestClient(app)

    choice = client.post("/auth/login", json={"identifier": "ana@pointage.test", "password": "correct-password"}).json()
    assert choice["status"] == "selection_required"
    assert choice["employments"][1] == {"employeeId": "emp2", "companyName": "Société B", "role": "HR"}
    pair = client.post("/auth/select-employee",
                       json={"selectionToken": choice["selectionToken"], "employeeId": "emp2"}).json()
    assert pair["status"] == "authenticated"
    me = client.get("/auth/me", headers={"Authorization": "Bearer " + pair["accessToken"]}).json()
    assert me == {"employeeId": "emp2", "userId": "usr1", "role": "HR"}

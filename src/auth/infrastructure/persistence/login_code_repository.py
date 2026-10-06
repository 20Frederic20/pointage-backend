"""SQLAlchemy adapter for the LoginCode aggregate — the versioned save
protocol (same as ``UserRepository``)."""

from datetime import datetime

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.domain.errors import ConflictError, NotFoundError

from ...domain.entities import LoginCode
from ...domain.repositories import ILoginCodeRepository
from ...domain.value_objects import LoginCodeId
from .models import LoginCodeModel


class LoginCodeRepository(ILoginCodeRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- read side ----------------------------------------------------------

    async def get_by_id(self, code_id: LoginCodeId) -> LoginCode:
        row = await self._session.get(LoginCodeModel, code_id.value)
        if row is None:
            raise NotFoundError(f"Login code {code_id.value} not found", context=code_id.value)
        return self._to_aggregate(row)

    async def exists(self, code_id: LoginCodeId) -> bool:
        row = await self._session.scalar(select(LoginCodeModel.id).where(LoginCodeModel.id == code_id.value))
        return row is not None

    async def find_latest_for_user(self, user_id: str) -> LoginCode | None:
        row = await self._session.scalar(
            select(LoginCodeModel)
            .where(LoginCodeModel.user_id == user_id)
            .order_by(LoginCodeModel.created_at.desc(), LoginCodeModel.id.desc())
            .limit(1)
        )
        return self._to_aggregate(row) if row is not None else None

    async def count_issued_since(self, user_id: str, since: datetime) -> int:
        stmt = (
            select(func.count())
            .select_from(LoginCodeModel)
            .where(LoginCodeModel.user_id == user_id, LoginCodeModel.created_at >= since)
        )
        return await self._session.scalar(stmt) or 0

    # -- write side ---------------------------------------------------------

    async def save(self, code: LoginCode) -> None:
        if code.version == 0:
            await self._insert(code)
        else:
            await self._update(code)
        code._advance_version()

    async def delete(self, code_id: LoginCodeId) -> None:
        await self._session.execute(delete(LoginCodeModel).where(LoginCodeModel.id == code_id.value))

    # -- helpers -------------------------------------------------------------

    async def _insert(self, code: LoginCode) -> None:
        try:
            await self._session.execute(
                insert(LoginCodeModel).values(
                    id=code.id.value,
                    user_id=code.user_id,
                    code_hash=code.code_hash,
                    expires_at=code.expires_at,
                    attempts=code.attempts,
                    consumed_at=code.consumed_at,
                    created_at=code.created_at,
                    updated_at=code.updated_at,
                    version_id=1,
                )
            )
        except IntegrityError as exc:
            raise ConflictError(
                f"Login code {code.id.value} conflicts with an existing row", context=code.id.value
            ) from exc

    async def _update(self, code: LoginCode) -> None:
        # Only the attempt count and the consumption change after issue.
        result = await self._session.execute(
            update(LoginCodeModel.__table__)
            .where(LoginCodeModel.id == code.id.value)
            .where(LoginCodeModel.version_id == code.version)
            .values(
                attempts=code.attempts,
                consumed_at=code.consumed_at,
                updated_at=code.updated_at,
                version_id=code.version + 1,
            )
        )
        if result.rowcount == 0:
            # Two guesses at the same time: one wins, the other is a 409 and
            # does not slip past the attempt counter.
            raise ConflictError(
                f"Login code {code.id.value} was modified concurrently (stale version {code.version})",
                context=code.id.value,
            )

    def _to_aggregate(self, row) -> LoginCode:
        return LoginCode(
            LoginCodeId(row.id),
            user_id=row.user_id,
            code_hash=row.code_hash,
            expires_at=row.expires_at,
            attempts=row.attempts,
            consumed_at=row.consumed_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
            version=row.version_id,
        )

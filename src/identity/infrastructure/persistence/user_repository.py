"""SQLAlchemy adapter for the User aggregate — the versioned save protocol."""

from datetime import UTC, datetime

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.domain.errors import ConflictError, NotFoundError
from core.domain.specifications import Specification

from ...domain.entities import User
from ...domain.repositories import IUserRepository
from ...domain.value_objects.ids import UserId
from ..translators import UsersSpecificationTranslator
from .models import UserModel


class UserRepository(IUserRepository):
    """Persists users whole-aggregate, with optimistic concurrency.

    Protocol (shared by every repository adapter): a never-persisted
    aggregate (``version == 0``) INSERTs — colliding with an existing id or
    the unique email is a :class:`ConflictError`; an already-persisted one
    UPDATEs ``WHERE id AND version_id = <loaded version>``, so a rowcount of
    zero means somebody else wrote first and raises :class:`ConflictError`
    instead of overwriting. After a durable write the aggregate's version is
    advanced. Timestamps are the domain's, not the database's.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._translator = UsersSpecificationTranslator()

    # -- read side ----------------------------------------------------------

    async def get_by_id(self, user_id: UserId) -> User:
        row = await self._session.get(UserModel, user_id.value)
        if row is None:
            raise NotFoundError(
                f"User {user_id} not found", context=user_id.value
            )
        return self._to_aggregate(row)

    async def find_by_email(self, email: str) -> User | None:
        normalized = email.strip().lower()
        row = await self._session.scalar(
            select(UserModel).where(UserModel.email == normalized)
        )
        return self._to_aggregate(row) if row is not None else None

    async def find(
        self, spec: Specification[User], *, limit: int = 50, offset: int = 0
    ) -> list[User]:
        stmt = (
            select(UserModel)
            .where(self._translator.translate(spec))
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.scalars(stmt)).all()
        return [self._to_aggregate(row) for row in rows]

    async def count(self, spec: Specification[User]) -> int:
        stmt = select(func.count()).select_from(UserModel).where(
            self._translator.translate(spec)
        )
        return await self._session.scalar(stmt) or 0

    async def exists_any(self) -> bool:
        row = await self._session.scalar(select(UserModel.id).limit(1))
        return row is not None

    async def count_active(self) -> int:
        stmt = (
            select(func.count())
            .select_from(UserModel)
            .where(UserModel.is_active.is_(True))
        )
        return await self._session.scalar(stmt) or 0

    # -- write side ---------------------------------------------------------

    async def save(self, user: User) -> None:
        if user.version == 0:
            await self._insert(user)
        else:
            await self._update(user)
        user._advance_version()

    async def delete(self, user_id: UserId) -> None:
        await self._session.execute(
            delete(UserModel).where(UserModel.id == user_id.value)
        )

    async def exists(self, user_id: UserId) -> bool:
        row = await self._session.scalar(
            select(UserModel.id).where(UserModel.id == user_id.value)
        )
        return row is not None

    # -- helpers -------------------------------------------------------------

    async def _insert(self, user: User) -> None:
        try:
            await self._session.execute(
                insert(UserModel).values(
                    id=user.id.value,
                    email=user.email,
                    password_hash=user.password_hash,
                    role=user.role,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    avatar_url=user.avatar_url,
                    is_active=user.is_active,
                    last_active_at=user.last_active_at,
                    # the domain owns timestamps at insert (single source of
                    # truth — the row stores what the aggregate says)
                    created_at=user.created_at or datetime.now(UTC),
                    updated_at=user.updated_at or datetime.now(UTC),
                    version_id=1,
                )
            )
        except IntegrityError as exc:
            raise ConflictError(
                f"User {user.id} already exists (id or email collision)",
                context=user.email,
            ) from exc

    async def _update(self, user: User) -> None:
        result = await self._session.execute(
            update(UserModel.__table__)
            .where(UserModel.id == user.id.value)
            .where(UserModel.version_id == user.version)
            .values(
                email=user.email,
                password_hash=user.password_hash,
                role=user.role,
                first_name=user.first_name,
                last_name=user.last_name,
                avatar_url=user.avatar_url,
                is_active=user.is_active,
                last_active_at=user.last_active_at,
                updated_at=user.updated_at or datetime.now(UTC),
                version_id=user.version + 1,
            )
        )
        if result.rowcount == 0:
            raise ConflictError(
                f"User {user.id} was modified concurrently "
                f"(stale version {user.version})",
                context=user.id.value,
            )

    def _to_aggregate(self, row) -> User:
        return User(
            UserId(row.id),
            email=row.email,
            password_hash=row.password_hash,
            role=row.role,
            first_name=row.first_name,
            last_name=row.last_name,
            avatar_url=row.avatar_url,
            is_active=row.is_active,
            last_active_at=row.last_active_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
            version=row.version_id,
        )

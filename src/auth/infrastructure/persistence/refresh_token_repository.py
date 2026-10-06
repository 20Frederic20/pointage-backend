"""SQLAlchemy adapter for the RefreshToken aggregate — the versioned save
protocol (same as ``UserRepository``)."""

from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.domain.errors import ConflictError, NotFoundError

from ...domain.entities import RefreshToken
from ...domain.repositories import IRefreshTokenRepository
from ...domain.value_objects import RefreshTokenId, TokenFamilyId
from .models import RefreshTokenModel


class RefreshTokenRepository(IRefreshTokenRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- read side ----------------------------------------------------------

    async def get_by_id(self, token_id: RefreshTokenId) -> RefreshToken:
        row = await self._session.get(RefreshTokenModel, token_id.value)
        if row is None:
            raise NotFoundError(f"Refresh token {token_id.value} not found", context=token_id.value)
        return self._to_aggregate(row)

    async def exists(self, token_id: RefreshTokenId) -> bool:
        row = await self._session.scalar(
            select(RefreshTokenModel.id).where(RefreshTokenModel.id == token_id.value)
        )
        return row is not None

    async def find_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        row = await self._session.scalar(
            select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        )
        return self._to_aggregate(row) if row is not None else None

    async def find_active_by_family(self, family_id: TokenFamilyId) -> list[RefreshToken]:
        rows = (
            await self._session.scalars(
                select(RefreshTokenModel).where(
                    RefreshTokenModel.family_id == family_id.value,
                    RefreshTokenModel.revoked_at.is_(None),
                )
            )
        ).all()
        return [self._to_aggregate(row) for row in rows]

    # -- write side ---------------------------------------------------------

    async def save(self, token: RefreshToken) -> None:
        if token.version == 0:
            await self._insert(token)
        else:
            await self._update(token)
        token._advance_version()

    async def delete(self, token_id: RefreshTokenId) -> None:
        await self._session.execute(delete(RefreshTokenModel).where(RefreshTokenModel.id == token_id.value))

    # -- helpers -------------------------------------------------------------

    async def _insert(self, token: RefreshToken) -> None:
        try:
            await self._session.execute(
                insert(RefreshTokenModel).values(
                    id=token.id.value,
                    user_id=token.user_id,
                    token_hash=token.token_hash,
                    family_id=token.family_id.value,
                    expires_at=token.expires_at,
                    session_expires_at=token.session_expires_at,
                    revoked_at=token.revoked_at,
                    created_at=token.created_at,
                    updated_at=token.updated_at,
                    version_id=1,
                )
            )
        except IntegrityError as exc:
            raise ConflictError(
                f"Refresh token {token.id.value} conflicts with an existing row", context=token.id.value
            ) from exc

    async def _update(self, token: RefreshToken) -> None:
        # Only revocation changes after issue; the hash, owner and expiry are fixed.
        result = await self._session.execute(
            update(RefreshTokenModel.__table__)
            .where(RefreshTokenModel.id == token.id.value)
            .where(RefreshTokenModel.version_id == token.version)
            .values(
                revoked_at=token.revoked_at,
                updated_at=token.updated_at,
                version_id=token.version + 1,
            )
        )
        if result.rowcount == 0:
            raise ConflictError(
                f"Refresh token {token.id.value} was modified concurrently (stale version {token.version})",
                context=token.id.value,
            )

    def _to_aggregate(self, row) -> RefreshToken:
        return RefreshToken(
            RefreshTokenId(row.id),
            user_id=row.user_id,
            token_hash=row.token_hash,
            family_id=TokenFamilyId(row.family_id),
            expires_at=row.expires_at,
            session_expires_at=row.session_expires_at,
            revoked_at=row.revoked_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
            version=row.version_id,
        )

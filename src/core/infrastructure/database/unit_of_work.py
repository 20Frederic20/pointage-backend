from types import TracebackType

from sqlalchemy.ext.asyncio.session import AsyncSession

from core.application import IUnitOfWork


class SQLAlchemyUnitOfWork(IUnitOfWork):
    """SQLAlchemy implementation of the unit-of-work transaction boundary.

    ``async with`` commits on clean exit and rolls back on exception. The
    application layer dispatches aggregate events *after* the block, so events
    are only published once the transaction is durable.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    async def __aenter__(self) -> IUnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()
            return
        try:
            await self.commit()
        except Exception:
            # Commit itself failed — roll the transaction back (best effort) so
            # a reused session isn't left in a partial state, then propagate.
            await self.rollback()
            raise

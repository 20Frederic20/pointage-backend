"""Interface-layer dependencies: the periods container, per request."""

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_db_session

from ..infrastructure import PeriodsContainer, build_periods_container


def get_periods(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> PeriodsContainer:
    """One periods container per request, wired over the request-scoped
    session and the app-wide event bus."""
    return build_periods_container(
        session=session,
        event_bus=request.app.state.container.event_bus,
    )

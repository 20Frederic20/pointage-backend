"""Interface-layer dependencies: the time calculation container, per request."""

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_db_session

from ..infrastructure import TimeCalculationContainer, build_time_calculation_container


def get_time_calculation(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> TimeCalculationContainer:
    """One time calculation container per request, wired over the
    request-scoped session and the app-wide event bus."""
    return build_time_calculation_container(
        session=session,
        event_bus=request.app.state.container.event_bus,
    )

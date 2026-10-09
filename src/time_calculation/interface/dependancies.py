"""Interface-layer dependencies: the time calculation container, per request."""

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_read_session, get_write_session

from ..infrastructure import TimeCalculationContainer, build_time_calculation_container


def get_time_calculation(
    request: Request,
    write_session: AsyncSession = Depends(get_write_session),
    read_session: AsyncSession = Depends(get_read_session),
) -> TimeCalculationContainer:
    """One time calculation container per request, wired over the
    request-scoped sessions (write: event store, read: read models) and the
    app-wide event bus."""
    return build_time_calculation_container(
        write_session=write_session,
        read_session=read_session,
        event_bus=request.app.state.container.event_bus,
    )

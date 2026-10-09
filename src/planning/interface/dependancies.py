"""Interface-layer dependencies: the planning container, per request."""

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_read_session, get_write_session

from ..infrastructure import PlanningContainer, build_planning_container


def get_planning(
    request: Request,
    write_session: AsyncSession = Depends(get_write_session),
    read_session: AsyncSession = Depends(get_read_session),
) -> PlanningContainer:
    """One planning container per request, wired over the request-scoped
    sessions (write: event store, read: read models) and the app-wide event bus."""
    return build_planning_container(
        write_session=write_session,
        read_session=read_session,
        event_bus=request.app.state.container.event_bus,
    )

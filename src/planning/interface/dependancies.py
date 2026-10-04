"""Interface-layer dependencies: the planning container, per request."""

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_db_session

from ..infrastructure import PlanningContainer, build_planning_container


def get_planning(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> PlanningContainer:
    """One planning container per request, wired over the request-scoped
    session and the app-wide event bus."""
    return build_planning_container(
        session=session,
        event_bus=request.app.state.container.event_bus,
    )

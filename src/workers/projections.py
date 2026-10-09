"""Projection worker — feeds the read database from the event store.

Every context lists its read-model projections in
``<context>.infrastructure.projections`` (one ``AggregateProjection`` per
aggregate); the runner applies every stored event, in global order, to the
projection of its stream type. Add a context's list below.
"""

from absences.infrastructure.projections import ABSENCES_PROJECTIONS
from adjustements.infrastructure.projections import ADJUSTMENTS_PROJECTIONS
from core.infrastructure.projections import ProjectionRunner
from core.infrastructure.projections.projection_runner import SessionFactory
from identity.infrastructure.projections import USERS_PROJECTIONS
from periods.infrastructure.projections import PERIODS_PROJECTIONS
from planning.infrastructure.projections import PLANNING_PROJECTIONS
from punch.infrastructure.projections import PUNCHES_PROJECTIONS
from time_calculation.infrastructure.projections import TIME_CALCULATION_PROJECTIONS

PROJECTIONS = [
    *USERS_PROJECTIONS,
    *PUNCHES_PROJECTIONS,
    *ADJUSTMENTS_PROJECTIONS,
    *ABSENCES_PROJECTIONS,
    *PLANNING_PROJECTIONS,
    *PERIODS_PROJECTIONS,
    *TIME_CALCULATION_PROJECTIONS,
]


def build_projection_worker(
    *,
    write_session_factory: SessionFactory,
    read_session_factory: SessionFactory,
    poll_interval: float = 0.2,
) -> ProjectionRunner:
    """Compose the runner over every context's projections."""
    return ProjectionRunner(
        write_session_factory=write_session_factory,
        read_session_factory=read_session_factory,
        projections=PROJECTIONS,
        poll_interval=poll_interval,
    )

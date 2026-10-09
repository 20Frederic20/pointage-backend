"""Read models of the adjustements context, fed from the event store."""

from core.infrastructure.projections import AggregateProjection

from ..domain.entities import Anomaly, RegularizationRequest
from ..domain.value_objects import AnomalyId, RegularizationRequestId
from .persistence.anomaly_repository import AnomalyRepository
from .persistence.event_sourced_anomaly_repository import ANOMALY_EVENT_TYPES, ANOMALY_STREAM
from .persistence.event_sourced_regularization_request_repository import (
    REGULARIZATION_REQUEST_EVENT_TYPES,
    REGULARIZATION_REQUEST_STREAM,
)
from .persistence.regularization_request_repository import RegularizationRequestRepository

ADJUSTMENTS_PROJECTIONS = [
    AggregateProjection(
        stream_type=ANOMALY_STREAM,
        aggregate_type=Anomaly,
        id_type=AnomalyId,
        repository_type=AnomalyRepository,
        event_types=ANOMALY_EVENT_TYPES,
    ),
    AggregateProjection(
        stream_type=REGULARIZATION_REQUEST_STREAM,
        aggregate_type=RegularizationRequest,
        id_type=RegularizationRequestId,
        repository_type=RegularizationRequestRepository,
        event_types=REGULARIZATION_REQUEST_EVENT_TYPES,
    ),
]

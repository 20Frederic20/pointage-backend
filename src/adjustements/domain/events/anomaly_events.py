from adjustements.domain import AnomalyId
from core.domain.events import BaseEvent


class AnomalyCreated(BaseEvent[AnomalyId]):

    def __init__(self, anomaly_id: AnomalyId) -> None:
        super().__init__()
        self._anomaly_id = anomaly_id

    def get_aggregate_id(self) -> AnomalyId:
        return self._anomaly_id

    def get_event_name(self) -> str:
        return "adjustments.anomaly.created"
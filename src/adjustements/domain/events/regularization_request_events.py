from ..value_objects import RegularizationRequestId
from core.domain.events import BaseEvent


class RegularizationRequestCreated(BaseEvent[RegularizationRequestId]):

    def __init__(self, regularization_request_id: RegularizationRequestId) -> None:
            super().__init__()
            self._regularization_request_id = regularization_request_id

    def get_aggregate_id(self) -> RegularizationRequestId:
        return self._regularization_request_id

    def get_event_name(self) -> str:
        return "adjustments.regularization_request.created"
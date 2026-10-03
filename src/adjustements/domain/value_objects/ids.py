from typing import Literal

from core.domain.value_objects import EntityId


class AnomalyId(EntityId[Literal["anomaly"]]):
    ...

class RegularizationRequestId(EntityId[Literal["regularization_request"]]):
    ...
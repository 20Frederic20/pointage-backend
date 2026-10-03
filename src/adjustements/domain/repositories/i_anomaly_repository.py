from adjustements.domain import Anomaly, AnomalyId
from core.domain.repositories import IRepository


class IAnomalyRepository(IRepository[Anomaly, AnomalyId]):
    ...
from adjustements.domain import RegularizationRequest, RegularizationRequestId
from core.domain.repositories import IRepository


class IRegularizationRequestRepository(IRepository[RegularizationRequest, RegularizationRequestId]):
    ...
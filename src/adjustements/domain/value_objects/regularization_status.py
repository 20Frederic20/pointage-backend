from enum import StrEnum


class RegularizationStatus(StrEnum):

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"
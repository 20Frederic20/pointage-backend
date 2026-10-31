from enum import StrEnum


class TimeEntryValidationStatus(StrEnum):
    """Whether a punch counts: an assisted punch waits for a manager's decision."""

    COUNTED = "COUNTED"
    PENDING = "PENDING"
    REJECTED = "REJECTED"

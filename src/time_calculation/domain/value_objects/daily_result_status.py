from enum import StrEnum


class DailyResultStatus(StrEnum):

    NORMAL = "NORMAL"
    ANOMALY = "ANOMALY"
    BLOCKED = "BLOCKED"
    VALIDATED = "VALIDATED"

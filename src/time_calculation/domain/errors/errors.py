from core.domain.errors import DomainError, Severity


class InvalidCalculationRuleVersionError(DomainError):
    """Raised when a rule version has invalid thresholds or does not start after the previous one."""

    code = "INVALID_CALCULATION_RULE_VERSION"
    http_status = 422
    severity = Severity.WARNING


class NoApplicableRuleVersionError(DomainError):
    """Raised when no calculation rule version applies to the work date."""

    code = "NO_APPLICABLE_RULE_VERSION"
    http_status = 409
    severity = Severity.WARNING


class NoPeriodForDateError(DomainError):
    """Raised when no period covers the work date."""

    code = "NO_PERIOD_FOR_DATE"
    http_status = 409
    severity = Severity.WARNING


class PeriodNotOpenForCalculationError(DomainError):
    """Raised when calculating a day of a locked or closed period."""

    code = "PERIOD_NOT_OPEN_FOR_CALCULATION"
    http_status = 409
    severity = Severity.WARNING


class DailyTimeResultValidatedError(DomainError):
    """Raised when recalculating or re-validating a validated daily result."""

    code = "DAILY_TIME_RESULT_VALIDATED"
    http_status = 409
    severity = Severity.WARNING


class BlockedDailyTimeResultError(DomainError):
    """Raised when validating a daily result blocked by an open blocking anomaly."""

    code = "BLOCKED_DAILY_TIME_RESULT"
    http_status = 409
    severity = Severity.WARNING

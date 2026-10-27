from core.domain.errors import DomainError, Severity


class AnomalyAlreadyDecidedError(DomainError):
    """Raised when a decision targets an anomaly that is no longer open."""

    code = "ANOMALY_ALREADY_DECIDED"
    http_status = 409
    severity = Severity.WARNING


class DecisionCommentRequiredError(DomainError):
    """Raised when a rejection comes without a comment."""

    code = "DECISION_COMMENT_REQUIRED"
    http_status = 422
    severity = Severity.WARNING


class DecisionCommentTooLongError(DomainError):
    """Raised when a decision comment exceeds the stored maximum length."""

    code = "DECISION_COMMENT_TOO_LONG"
    http_status = 422
    severity = Severity.WARNING

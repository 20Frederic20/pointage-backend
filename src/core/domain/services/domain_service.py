class DomainService:
    """Base class for stateless domain services.

    A domain service holds no state and implements a business rule that doesn't
    fit naturally on a single entity or aggregate (e.g. seat policies, contact
    merge rules). It stays a plain class: no ORM, no Pydantic, no I/O.

    ``service_name`` is optional metadata, e.g. for logging, tracing, or
    routing a service invocation.
    """

    def __init__(self, service_name: str | None = None) -> None:
        self.service_name = service_name

    def get_service_name(self) -> str | None:
        return self.service_name

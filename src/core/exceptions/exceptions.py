from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from core.domain.errors import DomainError
from core.schema import DomainErrorSchema


def register_exception_handlers(app: FastAPI) -> None:
    """Map domain errors to their HTTP wire schema.

    ``NotFoundError`` (404) and ``ConflictError`` (409) subclass ``DomainError``,
    so a single handler covers the whole hierarchy (Starlette resolves handlers
    by walking the exception's MRO).
    """

    @app.exception_handler(DomainError)
    async def _handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        schema = DomainErrorSchema(
            name=exc.name,
            code=exc.code,
            message=exc.message,
            severity=exc.severity.value,
            context=exc.context or "",
            http_status=exc.http_status,
            occurred_at=exc.occurred_at,
        )
        return JSONResponse(
            status_code=exc.http_status,
            # mode="json" renders datetime (occurred_at) to ISO strings so the
            # response is plain-JSON-serializable.
            content=schema.model_dump(mode="json", by_alias=True),
        )

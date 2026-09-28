from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from core.exceptions import register_exception_handlers
from core.settings import AppSettings, DatabaseSettings
from identity.interface.routers import directories_router, users_router
from lifespan import lifespan


def cors_config(allow_origins: list[str]) -> tuple[list[str], bool]:
    """CORS decision: (origins, allow_credentials).

    Credentials are only enabled for an explicit, non-wildcard allowlist —
    Starlette reflects *any* origin when ``["*"]`` is combined with
    ``allow_credentials=True``, which is the bug this avoids.
    """
    return allow_origins, bool(allow_origins) and "*" not in allow_origins


def _add_cors(app: FastAPI, settings: AppSettings) -> None:
    origins, allow_credentials = cors_config(settings.cors_origins)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def create_app(
    *,
    settings: AppSettings | None = None,
    database_settings: DatabaseSettings | None = None,
) -> FastAPI:
    """
    Application factory — middleware, exception handlers, routers, lifespan.
    """
    settings = settings or AppSettings()
    database_settings = database_settings or DatabaseSettings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.database_settings = database_settings

    _add_cors(app, settings)
    register_exception_handlers(app)

    app.include_router(users_router)
    app.include_router(directories_router)
    return app


app = create_app()

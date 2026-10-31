from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from absences.interface.routers import absence_types_router, absences_router
from adjustements.interface.routers import anomalies_router
from auth.interface.routers import auth_router
from core.exceptions import register_exception_handlers
from core.settings import AppSettings, AuthSettings, DatabaseSettings, MailSettings, StorageSettings
from identity.interface.routers import (
    directories_router,
    employee_assignments_router,
    employees_router,
    sites_router,
    users_router,
)
from lifespan import lifespan
from periods.interface.routers import periods_router
from planning.interface.routers import employee_schedules_router, time_profiles_router
from punch.interface.routers import manager_time_entries_router, time_entries_router
from time_calculation.interface.routers import (
    calculation_rule_versions_router,
    daily_time_results_router,
)


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
    auth_settings: AuthSettings | None = None,
    mail_settings: MailSettings | None = None,
    storage_settings: StorageSettings | None = None,
) -> FastAPI:
    """
    Application factory — middleware, exception handlers, routers, lifespan.
    """
    settings = settings or AppSettings()
    database_settings = database_settings or DatabaseSettings()
    # Fails fast at startup when JWT_SECRET is missing (no placeholder secret).
    auth_settings = auth_settings or AuthSettings()
    mail_settings = mail_settings or MailSettings()
    storage_settings = storage_settings or StorageSettings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.database_settings = database_settings
    app.state.auth_settings = auth_settings
    app.state.mail_settings = mail_settings
    app.state.storage_settings = storage_settings

    _add_cors(app, settings)
    register_exception_handlers(app)

    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(sites_router)
    app.include_router(directories_router)
    app.include_router(employees_router)
    app.include_router(employee_assignments_router)
    app.include_router(time_entries_router)
    app.include_router(manager_time_entries_router)
    app.include_router(absence_types_router)
    app.include_router(absences_router)
    app.include_router(time_profiles_router)
    app.include_router(employee_schedules_router)
    app.include_router(periods_router)
    app.include_router(calculation_rule_versions_router)
    app.include_router(daily_time_results_router)
    app.include_router(anomalies_router)
    return app


app = create_app()

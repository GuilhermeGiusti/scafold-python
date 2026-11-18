"""A borda HTTP: a tradução da telemetria para o framework e a montagem do app (ADR-011).

Este é o único arquivo de ``bootstrap/`` que importa o FastAPI. ``build_app`` recebe os use cases
prontos, e não a fundação: o mesmo código monta o app sobre o banco (entrypoint) e sobre os fakes
(testes).

Todas as rotas ficam sob ``/api/v1``. Um controller novo entra em ``_controllers`` e, se tiver
presenter próprio, em ``presenters``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.telemetry import TelemetryConfig
from starlette.exceptions import HTTPException

from scafold.bootstrap.composition import UseCases
from scafold.bootstrap.telemetry import Telemetry
from scafold.infrastructure.rest.example_controller import ExampleController
from scafold.infrastructure.rest.health_controller import HealthController
from scafold.infrastructure.rest.mappers.example_request_mapper import ExampleRequestMapper
from scafold.infrastructure.rest.presenters.example_presenter import ExamplePresenter
from scafold.infrastructure.rest.shared.error_presenter import ErrorPresenter

API_TITLE = "Scafold API"
API_VERSION = "1.0.0"

#: O prefixo de versão de todas as rotas.
API_PREFIX = "/api/v1"


def framework_telemetry(telemetry: Telemetry) -> TelemetryConfig:
    """A configuração da telemetria do FastAPI: ``FastAPI(telemetry=framework_telemetry(...))``.

    Sem ela o framework usaria os providers globais e montaria exportadores por conta própria ao
    encontrar as variáveis ``OTEL_EXPORTER_OTLP_*`` no ambiente. Nunca crie um app sem o argumento
    ``telemetry``.

    - ``tracer_provider`` e ``meter_provider``: os desta montagem.
    - ``metrics``: desligado junto com as métricas do processo.
    - ``logs``: desligado. O sinal de logs do framework envia a mensagem da exceção.
    - ``auto_configure``: desligado. Quem lê o ambiente é ``Settings``, e só ela.
    """
    return {
        "tracer_provider": telemetry.tracer_provider,
        "meter_provider": telemetry.meter_provider,
        "metrics": telemetry.meter_provider is not None,
        "logs": False,
        "auto_configure": False,
    }


def build_app(
    *,
    use_cases: UseCases,
    telemetry: Telemetry,
    expose_docs: bool,
    on_shutdown: Callable[[], Awaitable[None]] | None = None,
) -> FastAPI:
    """Monta o app com as rotas, a documentação por configuração e o formato de erro."""
    example_presenter = ExamplePresenter()
    presenters: tuple[ErrorPresenter, ...] = (example_presenter,)
    fallback = ErrorPresenter()

    controllers = (
        HealthController().router,
        ExampleController(
            create=use_cases.create_example,
            archive=use_cases.archive_example,
            get=use_cases.get_example,
            list_all=use_cases.list_examples,
            request_mapper=ExampleRequestMapper(),
            presenter=example_presenter,
        ).router,
    )

    async def present_error(_: Request, error: Exception) -> JSONResponse:
        for presenter in presenters:
            if presenter.knows(error):
                return presenter.present_error(error)
        return fallback.present_error(error)

    async def present_validation_error(_: Request, error: Exception) -> JSONResponse:
        assert isinstance(error, RequestValidationError)
        return fallback.present_validation_error(error)

    async def present_http_error(_: Request, error: Exception) -> JSONResponse:
        assert isinstance(error, HTTPException)
        return fallback.present_http_error(error)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        # O pool é fechado no mesmo event loop que o abriu.
        if on_shutdown is not None:
            await on_shutdown()

    # A tela e o `openapi.json` só são servidos quando a configuração liga. O documento existe
    # sempre: `app.openapi()` não depende dessas rotas, e é ele que os testes leem.
    app = FastAPI(
        title=API_TITLE,
        version=API_VERSION,
        telemetry=framework_telemetry(telemetry),
        lifespan=lifespan,
        docs_url="/docs" if expose_docs else None,
        openapi_url="/openapi.json" if expose_docs else None,
        redoc_url=None,
    )
    for router in controllers:
        app.include_router(router, prefix=API_PREFIX)
    app.add_exception_handler(RequestValidationError, present_validation_error)
    app.add_exception_handler(HTTPException, present_http_error)
    for presenter in presenters:
        for error_type in presenter.PRESENTABLE:
            app.add_exception_handler(error_type, present_error)
    # O defeito também passa pelo presenter: 500 com `internal_error`, sem detalhe. O framework
    # relança a exceção para o servidor registrá-la.
    app.add_exception_handler(Exception, present_error)
    return app

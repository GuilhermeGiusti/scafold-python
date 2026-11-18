"""A montagem compartilhada pelos processos: o único lugar que conhece porta, adaptador e decorator.

``build_foundation`` reúne o que a API, a CLI e a tela Streamlit têm em comum, e **não importa
nenhuma borda**: quem acrescenta HTTP, linha de comando ou tela é o módulo de cada uma, em
``bootstrap/``. O job da outbox usa as mesmas peças por ``bootstrap/outbox_job.py``.

**Montar não conecta.** O banco só é contatado no primeiro uso.

Três pontos abrem span, e todos recebem o MESMO ``TracerProvider``: a borda HTTP (o FastAPI), o
``UseCaseObserver`` e a ``UnitOfWork`` com o ouvinte de queries. Como cada span fica corrente
enquanto o trecho dele roda, uma requisição vira um trace só: rota, use case, transação e query.

**Nenhum use case sai cru.** ``build_use_cases`` envolve cada um no decorator do seu contrato, com o
rótulo literal em snake_case, e os campos de ``UseCases`` são tipados pelo contrato.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from opentelemetry.metrics import MeterProvider

from scafold.applications.commands.archive_example_command import ArchiveExampleCommand
from scafold.applications.commands.create_example_command import CreateExampleCommand
from scafold.applications.handlers.all_events_handler import AllEventsHandler
from scafold.applications.handlers.example_created_handler import ExampleCreatedHandler
from scafold.applications.ports.category_gateway import ICategoryGateway
from scafold.applications.ports.example_reader import IExampleReader
from scafold.applications.ports.outbox_metrics import IOutboxMetrics
from scafold.applications.queries.example_summary import ExampleSummary
from scafold.applications.queries.example_view import ExampleView
from scafold.applications.queries.get_example_query import GetExampleQuery
from scafold.applications.queries.list_examples_query import ListExamplesQuery
from scafold.applications.shared.use_case import (
    AsyncExecuterUseCase,
    AsyncUnitUseCase,
    AsyncUseCase,
)
from scafold.applications.usecases.archive_example_use_case import ArchiveExampleUseCase
from scafold.applications.usecases.create_example_use_case import CreateExampleUseCase
from scafold.applications.usecases.get_example_use_case import GetExampleUseCase
from scafold.applications.usecases.list_examples_use_case import ListExamplesUseCase
from scafold.applications.usecases.purge_archived_examples_use_case import (
    PurgeArchivedExamplesUseCase,
)
from scafold.bootstrap.settings import Settings
from scafold.bootstrap.telemetry import Telemetry
from scafold.domain.bounded_context_example.repositories.example_repository import (
    IExampleRepository,
)
from scafold.domain.bounded_context_example.value_objects.example_id import ExampleId
from scafold.domain.outbox.ports.integration_writer import IIntegrationWriter
from scafold.domain.shared.events.event_base import IDomainEventDispatcher
from scafold.domain.shared.persistence.unit_of_work import IUnitOfWork
from scafold.infrastructure.events.event_dispatcher import DomainEventDispatcher
from scafold.infrastructure.events.event_manager import DomainEventManager
from scafold.infrastructure.events.event_metrics import IDomainEventMetrics
from scafold.infrastructure.events.logging_domain_event_metrics import LoggingDomainEventMetrics
from scafold.infrastructure.events.opentelemetry_domain_event_metrics import (
    OpenTelemetryDomainEventMetrics,
)
from scafold.infrastructure.events.outbox_writer import OutboxWriter
from scafold.infrastructure.external.external_category_gateway import ExternalCategoryGateway
from scafold.infrastructure.external.fake_category_api import FakeCategoryApi
from scafold.infrastructure.external.mappers.category_payload_mapper import (
    CategoryPayloadMapper,
)
from scafold.infrastructure.external.metrics.logging_translation_error_metrics import (
    LoggingTranslationErrorMetrics,
)
from scafold.infrastructure.external.metrics.opentelemetry_translation_error_metrics import (
    OpenTelemetryTranslationErrorMetrics,
)
from scafold.infrastructure.external.metrics.translation_error_metrics import (
    ITranslationErrorMetrics,
)
from scafold.infrastructure.observability.async_observed_use_cases import (
    AsyncObservedExecuterUseCase,
    AsyncObservedUnitUseCase,
    AsyncObservedUseCase,
)
from scafold.infrastructure.observability.logging_outbox_metrics import LoggingOutboxMetrics
from scafold.infrastructure.observability.logging_use_case_metrics import LoggingUseCaseMetrics
from scafold.infrastructure.observability.opentelemetry_outbox_metrics import (
    OpenTelemetryOutboxMetrics,
)
from scafold.infrastructure.observability.opentelemetry_use_case_metrics import (
    OpenTelemetryUseCaseMetrics,
)
from scafold.infrastructure.observability.use_case_metrics import IUseCaseMetrics
from scafold.infrastructure.observability.use_case_observer import UseCaseObserver
from scafold.infrastructure.persistence.bounded_context_example.mappers.example_row_mapper import (
    ExampleRowMapper,
)
from scafold.infrastructure.persistence.bounded_context_example.sql_example_reader import (
    SqlExampleReader,
)
from scafold.infrastructure.persistence.bounded_context_example.sql_example_repository import (
    SqlExampleRepository,
)
from scafold.infrastructure.persistence.metrics.logging_persistence_metrics import (
    LoggingPersistenceMetrics,
)
from scafold.infrastructure.persistence.metrics.opentelemetry_persistence_metrics import (
    OpenTelemetryPersistenceMetrics,
)
from scafold.infrastructure.persistence.metrics.persistence_metrics import IPersistenceMetrics
from scafold.infrastructure.persistence.persistence import Persistence, open_persistence

#: O logger raiz do projeto. Todo logger da aplicação fica sob ele.
LOGGER_NAME = "scafold"


def utc_now() -> datetime:
    """O relógio dos use cases. Injetado, para os testes fixarem o instante."""
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class MetricsAdapters:
    """Um adaptador por porta de métricas, todos do mesmo tipo: OpenTelemetry ou log."""

    use_case: IUseCaseMetrics
    persistence: IPersistenceMetrics
    domain_events: IDomainEventMetrics
    translation: ITranslationErrorMetrics
    outbox: IOutboxMetrics


def build_metrics_adapters(
    meter_provider: MeterProvider | None, logger: logging.Logger
) -> MetricsAdapters:
    """Com métricas ligadas, os adaptadores OpenTelemetry. Desligadas, os de log, em DEBUG.

    Desligar não apaga a medição: só a tira do envio e a escreve no log. Uma porta nova de
    métricas entra aqui, com os dois adaptadores dela.
    """
    if meter_provider is None:
        return MetricsAdapters(
            use_case=LoggingUseCaseMetrics(logger),
            persistence=LoggingPersistenceMetrics(logger),
            domain_events=LoggingDomainEventMetrics(logger),
            translation=LoggingTranslationErrorMetrics(logger),
            outbox=LoggingOutboxMetrics(logger),
        )
    return MetricsAdapters(
        use_case=OpenTelemetryUseCaseMetrics(meter_provider),
        persistence=OpenTelemetryPersistenceMetrics(meter_provider),
        domain_events=OpenTelemetryDomainEventMetrics(meter_provider),
        translation=OpenTelemetryTranslationErrorMetrics(meter_provider),
        outbox=OpenTelemetryOutboxMetrics(meter_provider),
    )


def build_event_manager(
    *, metrics: IDomainEventMetrics, logger: logging.Logger
) -> DomainEventManager:
    """Um manager por processo, com todos os handlers registrados numa única chamada.

    A saída de cada handler é decidida aqui: neste scaffold, o log. Um handler novo entra nesta
    lista, com a sua saída.
    """
    manager = DomainEventManager(metrics=metrics)
    manager.register(
        ExampleCreatedHandler(logger.info),
        AllEventsHandler(lambda payload: logger.debug("evento de dominio: %s", payload)),
    )
    return manager


@dataclass(frozen=True, slots=True, kw_only=True)
class UseCases:
    """O que as bordas recebem. Tipado pelo CONTRATO: o objeto é o decorator, e a borda não sabe."""

    create_example: AsyncUseCase[CreateExampleCommand, ExampleId]
    archive_example: AsyncUnitUseCase[ArchiveExampleCommand]
    get_example: AsyncUseCase[GetExampleQuery, ExampleView]
    list_examples: AsyncUseCase[ListExamplesQuery, list[ExampleSummary]]
    purge_archived_examples: AsyncExecuterUseCase


def build_use_cases(
    *,
    unit_of_work: IUnitOfWork,
    repository: IExampleRepository,
    reader: IExampleReader,
    gateway: ICategoryGateway,
    writer: IIntegrationWriter,
    dispatcher: IDomainEventDispatcher,
    clock: Callable[[], datetime],
    observer: UseCaseObserver,
) -> UseCases:
    """Recebe só portas: o mesmo código monta os use cases sobre o banco e sobre os fakes."""
    return UseCases(
        create_example=AsyncObservedUseCase(
            CreateExampleUseCase(
                unit_of_work=unit_of_work,
                repository=repository,
                gateway=gateway,
                writer=writer,
                dispatcher=dispatcher,
                clock=clock,
            ),
            use_case="create_example",
            observer=observer,
        ),
        archive_example=AsyncObservedUnitUseCase(
            ArchiveExampleUseCase(
                unit_of_work=unit_of_work, repository=repository, dispatcher=dispatcher, clock=clock
            ),
            use_case="archive_example",
            observer=observer,
        ),
        get_example=AsyncObservedUseCase(
            GetExampleUseCase(repository=repository),
            use_case="get_example",
            observer=observer,
        ),
        list_examples=AsyncObservedUseCase(
            ListExamplesUseCase(reader=reader),
            use_case="list_examples",
            observer=observer,
        ),
        purge_archived_examples=AsyncObservedExecuterUseCase(
            PurgeArchivedExamplesUseCase(unit_of_work=unit_of_work, repository=repository),
            use_case="purge_archived_examples",
            observer=observer,
        ),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class Foundation:
    """O que a montagem entrega a quem for usar."""

    settings: Settings
    telemetry: Telemetry
    logger: logging.Logger
    metrics: MetricsAdapters
    persistence: Persistence
    #: Referência forte: o sinal `blinker` guarda só uma referência fraca ao receiver do manager.
    event_manager: DomainEventManager
    use_cases: UseCases

    async def close(self) -> None:
        """Fecha o pool. Uma vez, no encerramento, no mesmo event loop que o abriu."""
        await self.persistence.close()


def build_foundation(
    *, settings: Settings, telemetry: Telemetry, clock: Callable[[], datetime] = utc_now
) -> Foundation:
    """Uma vez por processo, depois de a configuração ser aceita."""
    logger = logging.getLogger(LOGGER_NAME)
    metrics = build_metrics_adapters(telemetry.meter_provider, logger)
    persistence = open_persistence(
        settings.database_url, metrics.persistence, telemetry.tracer_provider
    )
    unit_of_work = persistence.unit_of_work
    observer = UseCaseObserver(
        metrics=metrics.use_case, logger=logger, tracer_provider=telemetry.tracer_provider
    )
    use_cases = build_use_cases(
        unit_of_work=unit_of_work,
        repository=SqlExampleRepository(unit_of_work, ExampleRowMapper()),
        reader=SqlExampleReader(unit_of_work),
        gateway=ExternalCategoryGateway(
            api=FakeCategoryApi(), mapper=CategoryPayloadMapper(), metrics=metrics.translation
        ),
        writer=OutboxWriter(
            dispatcher=settings.outbox_dispatcher, unit_of_work=unit_of_work, metrics=metrics.outbox
        ),
        dispatcher=DomainEventDispatcher(metrics=metrics.domain_events),
        clock=clock,
        observer=observer,
    )
    return Foundation(
        settings=settings,
        telemetry=telemetry,
        logger=logger,
        metrics=metrics,
        persistence=persistence,
        event_manager=build_event_manager(metrics=metrics.domain_events, logger=logger),
        use_cases=use_cases,
    )

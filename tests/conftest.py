"""Fixtures e steps compartilhados por toda a suíte.

Pedir ``database_url`` (ou uma fixture que dependa dela) é o que exige Docker. Os cenários que
pedem o banco ou o broker levam a tag ``@integration`` no ``.feature``; o lado ``postgres`` do teste
de contrato leva a marca pelo parâmetro. ``uv run pytest -m "not integration"`` roda sem Docker.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import asyncpg
import pytest
from httpx2 import Response
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pytest_bdd import parsers, then
from testcontainers.community.postgres import PostgresContainer
from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network

from scafold.applications.errors.example_not_found import ExampleNotFound
from scafold.applications.ports.example_reader import IExampleReader
from scafold.bootstrap.settings import ConfigurationError
from scafold.domain.bounded_context_example.errors.duplicate_item import DuplicateItem
from scafold.domain.bounded_context_example.errors.invalid_label import InvalidLabel
from scafold.domain.bounded_context_example.errors.invalid_transition import InvalidTransition
from scafold.domain.bounded_context_example.errors.label_taken import LabelTaken
from scafold.domain.bounded_context_example.repositories.example_repository import (
    IExampleRepository,
)
from scafold.domain.bounded_context_order.errors.empty_order import EmptyOrder
from scafold.domain.bounded_context_order.errors.invalid_quantity import InvalidQuantity
from scafold.domain.bounded_context_order.errors.invalid_tracking_code import (
    InvalidTrackingCode,
)
from scafold.domain.outbox.errors.invalid_integration_event import InvalidIntegrationEvent
from scafold.domain.shared.persistence.unit_of_work import IUnitOfWork
from scafold.infrastructure.events.event_manager import DomainEventManager
from scafold.infrastructure.external.errors.unmapped_payload import UnmappedPayload
from scafold.infrastructure.persistence.bounded_context_example.mappers.example_row_mapper import (
    ExampleRowMapper,
)
from scafold.infrastructure.persistence.bounded_context_example.sql_example_reader import (
    SqlExampleReader,
)
from scafold.infrastructure.persistence.bounded_context_example.sql_example_repository import (
    SqlExampleRepository,
)
from scafold.infrastructure.persistence.persistence import Persistence, open_persistence
from scafold.infrastructure.persistence.unit_of_work import OutsideUnitOfWork

from .support.fakes import (
    FakeUnitOfWork,
    InMemoryExampleReader,
    InMemoryExampleRepository,
    RecordingDomainEventMetrics,
)
from .support.persistence_metrics import RecordingPersistenceMetrics
from .support.scene import Scene, build_scene

type Run =Callable[[Coroutine[Any, Any, Any]], Any]

PROJECT_ROOT = Path(__file__).resolve().parent.parent

POSTGRES_IMAGE = "postgres:18.6-alpine"
FLYWAY_IMAGE = "flyway/flyway:13.4-alpine"

#: `<location no container>: <pasta no projeto>`. O mesmo Flyway da stack local.
FLYWAY_LOCATIONS = {
    "/flyway/sql/example": PROJECT_ROOT / "migrations" / "example",
    "/flyway/sql/outbox": PROJECT_ROOT / "migrations" / "outbox",
}

#: O alias do Postgres na rede do teste: é o host que o Flyway usa.
_POSTGRES_ALIAS = "postgres"

#: Tabelas que o TRUNCATE entre cenários não toca.
_KEEP_TABLES = frozenset({"flyway_schema_history"})

# O cenário diz o motivo na língua do negócio; só aqui ele vira a classe do erro.
REASONS: dict[str, type[Exception]] = {
    "nome inválido": InvalidLabel,
    "item repetido": DuplicateItem,
    "transição inválida": InvalidTransition,
    "nome já usado": LabelTaken,
    "example inexistente": ExampleNotFound,
    "pedido vazio": EmptyOrder,
    "quantidade inválida": InvalidQuantity,
    "código de rastreio inválido": InvalidTrackingCode,
    "configuração inválida": ConfigurationError,
    "evento de integração inválido": InvalidIntegrationEvent,
    "escrita fora da transação": OutsideUnitOfWork,
    "payload sem tradução": UnmappedPayload,
}


# ---------------------------------------------------------------------------------------------
# Execução e isolamento
# ---------------------------------------------------------------------------------------------


@pytest.fixture
def run() -> Iterator[Run]:
    """Executa código async a partir de steps síncronos, sempre no mesmo event loop do cenário."""
    with asyncio.Runner() as runner:
        yield runner.run


@pytest.fixture(autouse=True)
def _isolated_domain_signal() -> Iterator[None]:
    """O sinal ``blinker`` é global por nome: o ``clear`` desconecta os receivers do processo e
    impede que handlers registrados num cenário vazem para o próximo."""
    yield
    DomainEventManager(metrics=RecordingDomainEventMetrics()).clear()


@pytest.fixture(autouse=True)
def _isolated_root_logger() -> Iterator[None]:
    """``configure_logging`` troca os handlers do logger raiz. Aqui eles voltam ao que eram."""
    root = logging.getLogger()
    handlers, level = list(root.handlers), root.level
    yield
    root.handlers = handlers
    root.setLevel(level)


@pytest.fixture
def scene() -> Scene:
    """Os use cases do processo sobre os fakes, novos a cada cenário."""
    return build_scene()


@pytest.fixture
def spans() -> InMemorySpanExporter:
    """Os spans encerrados, na ordem em que terminaram. Nada sai do processo."""
    return InMemorySpanExporter()


@pytest.fixture
def tracer_provider(spans: InMemorySpanExporter) -> TracerProvider:
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(spans))
    return provider


# ---------------------------------------------------------------------------------------------
# Postgres real, migrado pelo Flyway, só para quem pede `database_url`
# ---------------------------------------------------------------------------------------------


def _run_flyway(network: Network, postgres: PostgresContainer) -> None:
    """Roda ``flyway migrate`` até o fim e falha o setup se ele falhar."""
    flyway = (
        DockerContainer(FLYWAY_IMAGE)
        .with_network(network)
        .with_env("FLYWAY_URL", f"jdbc:postgresql://{_POSTGRES_ALIAS}:5432/{postgres.dbname}")
        .with_env("FLYWAY_USER", postgres.username)
        .with_env("FLYWAY_PASSWORD", postgres.password)
        .with_env("FLYWAY_LOCATIONS", ",".join(f"filesystem:{p}" for p in FLYWAY_LOCATIONS))
        .with_env("FLYWAY_CLEAN_DISABLED", "true")
        .with_command("-connectRetries=30 migrate")
    )
    for container_path, host_path in FLYWAY_LOCATIONS.items():
        flyway = flyway.with_volume_mapping(str(host_path), container_path, "ro")
    flyway.start()
    try:
        status = flyway.get_wrapped_container().wait()["StatusCode"]
        if status != 0:
            stdout, stderr = flyway.get_logs()
            raise RuntimeError(f"flyway migrate falhou ({status}):\n{stdout!r}\n{stderr!r}")
    finally:
        flyway.stop()


async def _truncate_all(dsn: str) -> None:
    connection = await asyncpg.connect(dsn)
    try:
        rows = await connection.fetch("SELECT tablename FROM pg_tables WHERE schemaname='public'")
        names = [row["tablename"] for row in rows if row["tablename"] not in _KEEP_TABLES]
        if names:
            await connection.execute(f"TRUNCATE {', '.join(names)} CASCADE")
    finally:
        await connection.close()


@pytest.fixture(scope="session")
def _postgres_dsn() -> Iterator[str]:
    """Um Postgres por sessão, migrado pelo Flyway, numa rede própria."""
    with Network() as network:
        postgres = (
            PostgresContainer(POSTGRES_IMAGE, driver=None)
            .with_network(network)
            .with_network_aliases(_POSTGRES_ALIAS)
        )
        with postgres:
            _run_flyway(network, postgres)
            # `sslmode=disable`: o container não serve TLS.
            yield f"{postgres.get_connection_url()}?sslmode=disable"


@pytest.fixture
def database_url(_postgres_dsn: str) -> str:
    """A URL do contrato (``postgresql://``), sobre tabelas vazias a cada cenário."""
    asyncio.run(_truncate_all(_postgres_dsn))
    return _postgres_dsn


@pytest.fixture
def persistence(
    database_url: str, run: Run, tracer_provider: TracerProvider
) -> Iterator[Persistence]:
    """A camada de dados montada como o processo a monta, sobre o loop do cenário."""
    built =open_persistence(database_url, RecordingPersistenceMetrics(), tracer_provider)
    yield built
    run(built.close())


# ---------------------------------------------------------------------------------------------
# Teste de contrato: o mesmo cenário contra o fake e contra o adaptador SQL
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Backend:
    """Unit of Work, repositório e leitor de UMA implementação: todos fakes ou todos SQL."""

    unit_of_work: IUnitOfWork
    repository: IExampleRepository
    reader: IExampleReader


@pytest.fixture(params=["fake", pytest.param("postgres", marks=pytest.mark.integration)])
def backend(request: pytest.FixtureRequest) -> Backend:
    """``fake`` roda sem Docker; ``postgres`` pede a fixture ``persistence`` e sobe o banco."""
    if request.param == "fake":
        uow = FakeUnitOfWork()
        return Backend(uow, InMemoryExampleRepository(uow), InMemoryExampleReader(uow.store))
    persistence: Persistence = request.getfixturevalue("persistence")
    sql_uow = persistence.unit_of_work
    return Backend(
        sql_uow, SqlExampleRepository(sql_uow, ExampleRowMapper()), SqlExampleReader(sql_uow)
    )


# ---------------------------------------------------------------------------------------------
# Steps compartilhados
# ---------------------------------------------------------------------------------------------


@then(parsers.parse("a operação é recusada por {reason}"))
def _(outcome: object, reason: str) -> None:
    assert type(outcome) is REASONS[reason], outcome


@then(parsers.parse("a resposta tem o status {status:d}"))
def _(outcome: Response, status: int) -> None:
    assert outcome.status_code == status, outcome.text


@then(parsers.parse('o erro tem o código "{code}"'))
def _(outcome: Response, code: str) -> None:
    assert outcome.json()["code"] == code

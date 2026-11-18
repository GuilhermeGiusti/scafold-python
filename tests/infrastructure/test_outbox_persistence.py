import logging
import time
from uuid import UUID

import asyncpg
import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import format_trace_id
from pytest_bdd import given, parsers, scenarios, then, when

from scafold.applications.usecases.create_example_use_case import example_created_event
from scafold.applications.usecases.outbox_drain_use_case import OutboxDrainUseCase
from scafold.domain.bounded_context_example.aggregates.example import Example
from scafold.domain.bounded_context_example.value_objects.category import Category
from scafold.domain.outbox.dispatchers import KNOWN_DISPATCHERS, RABBITMQ_DISPATCHER
from scafold.domain.outbox.value_objects.published import Published
from scafold.infrastructure.events.outbox_writer import OutboxWriter
from scafold.infrastructure.persistence.bounded_context_example.mappers.example_row_mapper import (
    ExampleRowMapper,
)
from scafold.infrastructure.persistence.bounded_context_example.sql_example_repository import (
    SqlExampleRepository,
)
from scafold.infrastructure.persistence.outbox.sql_outbox_repository import SqlOutboxRepository
from scafold.infrastructure.persistence.persistence import Persistence
from scafold.infrastructure.persistence.unit_of_work import OutsideUnitOfWork

from ..conftest import Run
from ..support.fakes import RecordingOutboxMetrics, ScriptedDispatcher
from ..support.scene import NOW

scenarios("infrastructure/outbox_persistence.feature")


class Boom(Exception):
    """Uma falha depois das gravações, antes do commit."""


@pytest.fixture
def writer(persistence: Persistence) -> OutboxWriter:
    return OutboxWriter(
        dispatcher=RABBITMQ_DISPATCHER,
        unit_of_work=persistence.unit_of_work,
        metrics=RecordingOutboxMetrics(),
    )


@pytest.fixture
def trace_ids() -> list[str]:
    return []


async def write_state_and_event(
    persistence: Persistence, writer: OutboxWriter, *, fail: bool = False
) -> UUID:
    example = Example.create(label="Relatório", category=Category.STANDARD, now=NOW)
    repository = SqlExampleRepository(persistence.unit_of_work, ExampleRowMapper())
    async with persistence.unit_of_work.transaction("create_example"):
        await repository.add(example)
        message_id = await writer.write(example_created_event(example))
        if fail:
            raise Boom()
    return message_id


# A gravação roda dentro de um span, como a borda e o decorator do use case fazem: sem span, o
# gravador recusa, porque o `correlation_id` ficaria vazio.
@when("gravo o Example \"Relatório\" e o evento de integração na mesma transação")
@given("o Example \"Relatório\" e o evento de integração gravados")
def _(
    run: Run,
    persistence: Persistence,
    writer: OutboxWriter,
    tracer_provider: TracerProvider,
    trace_ids: list[str],
) -> None:
    with tracer_provider.get_tracer("test").start_as_current_span("request") as span:
        trace_ids.append(format_trace_id(span.get_span_context().trace_id))
        run(write_state_and_event(persistence, writer))


@when(
    "gravo o Example \"Relatório\" e o evento na mesma transação, e ela falha antes do commit"
)
def _(run: Run, persistence: Persistence, writer: OutboxWriter, tracer_provider: TracerProvider) -> None:
    with tracer_provider.get_tracer("test").start_as_current_span("request"):
        with pytest.raises(Boom):
            run(write_state_and_event(persistence, writer, fail=True))


@when("gravo o evento de integração fora de uma transação", target_fixture="outcome")
def _(run: Run, writer: OutboxWriter, tracer_provider: TracerProvider) -> None | OutsideUnitOfWork:
    example = Example.create(label="Relatório", category=Category.STANDARD, now=NOW)
    with tracer_provider.get_tracer("test").start_as_current_span("request"):
        try:
            run(writer.write(example_created_event(example)))
        except OutsideUnitOfWork as error:
            return error
    return None


@when("a drenagem sobre o banco roda um ciclo com o broker aceitando")
def _(run: Run, persistence: Persistence) -> None:
    drain = OutboxDrainUseCase(
        unit_of_work=persistence.unit_of_work,
        repository=SqlOutboxRepository(persistence.unit_of_work),
        dispatcher=ScriptedDispatcher(Published()),
        metrics=RecordingOutboxMetrics(),
        batch_size=10,
        retry_countdown_seconds=30,
        stop_requested=lambda: False,
        known_dispatchers=KNOWN_DISPATCHERS,
        logger=logging.getLogger("scafold"),
        clock=time.monotonic,
    )
    run(drain.execute())


async def fetch(database_url: str, sql: str) -> list[asyncpg.Record]:
    connection = await asyncpg.connect(database_url)
    try:
        rows: list[asyncpg.Record] = await connection.fetch(sql)
        return rows
    finally:
        await connection.close()


@then(parsers.parse('a tabela "{table}" tem {count:d} linhas'))
def _(run: Run, database_url: str, table: str, count: int) -> None:
    rows = run(fetch(database_url, f"SELECT 1 FROM {table}"))
    assert len(rows) == count


@then(parsers.parse('a tabela "outbox_message" tem {count:d} linhas com o status "{status}"'))
def _(run: Run, database_url: str, count: int, status: str) -> None:
    rows = run(fetch(database_url, "SELECT status FROM outbox_message"))
    assert [row["status"] for row in rows] == [status] * count


@then(
    parsers.parse('a mensagem gravada foi carimbada "{dispatcher}" com o id do trace da gravação')
)
def _(run: Run, database_url: str, trace_ids: list[str], dispatcher: str) -> None:
    [row] = run(fetch(database_url, "SELECT dispatcher, correlation_id FROM outbox_message"))
    assert (row["dispatcher"], row["correlation_id"]) == (dispatcher, trace_ids[-1])

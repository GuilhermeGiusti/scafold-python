import logging
import time
from uuid import uuid4

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from scafold.applications.commands.drain_result import DrainResult
from scafold.applications.usecases.outbox_drain_use_case import OutboxDrainUseCase
from scafold.domain.outbox.dispatchers import KNOWN_DISPATCHERS, RABBITMQ_DISPATCHER
from scafold.domain.outbox.value_objects.pending_message import PendingMessage
from scafold.domain.outbox.value_objects.permanent_failure import PermanentFailure
from scafold.domain.outbox.value_objects.published import Published
from scafold.domain.outbox.value_objects.transient_failure import TransientFailure

from ..conftest import Run
from ..support.fakes import (
    FakeUnitOfWork,
    InMemoryOutboxRepository,
    QueuedMessage,
    RecordingOutboxMetrics,
    ScriptedDispatcher,
)

scenarios("applications/outbox_drain.feature")


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def repository(unit_of_work: FakeUnitOfWork) -> InMemoryOutboxRepository:
    return InMemoryOutboxRepository(unit_of_work)


@pytest.fixture
def metrics() -> RecordingOutboxMetrics:
    return RecordingOutboxMetrics()


@pytest.fixture
def dispatcher() -> ScriptedDispatcher:
    """O padrão: o broker aceita. Um `Dado` troca."""
    return ScriptedDispatcher(Published())


@given(parsers.parse('uma mensagem pendente do evento "{event_type}"'), target_fixture="queued")
def _(repository: InMemoryOutboxRepository, event_type: str) -> QueuedMessage:
    return repository.enqueue(
        PendingMessage(
            id=uuid4(),
            destination="example",
            event_type=event_type,
            event_version=1,
            payload={"id": "1"},
            aggregate_type="example",
            aggregate_id="1",
            correlation_id="0" * 32,
            trace_context=None,
            dispatcher=RABBITMQ_DISPATCHER,
            attempts=0,
            routing_key=event_type,
        )
    )


@given(parsers.parse("a mensagem com {attempts:d} tentativas"))
def _(queued: QueuedMessage, attempts: int) -> None:
    queued.attempts = attempts


@given("o broker aceitando as publicações", target_fixture="dispatcher")
def _() -> ScriptedDispatcher:
    return ScriptedDispatcher(Published())


@given("o broker falhando de forma transitória", target_fixture="dispatcher")
def _() -> ScriptedDispatcher:
    return ScriptedDispatcher(TransientFailure("broker fora do ar"))


@given("o broker falhando de forma permanente", target_fixture="dispatcher")
def _() -> ScriptedDispatcher:
    return ScriptedDispatcher(PermanentFailure("exchange inexistente"))


@when("a drenagem roda um ciclo", target_fixture="outcome")
def _(
    run: Run,
    unit_of_work: FakeUnitOfWork,
    repository: InMemoryOutboxRepository,
    dispatcher: ScriptedDispatcher,
    metrics: RecordingOutboxMetrics,
) -> DrainResult:
    drain = OutboxDrainUseCase(
        unit_of_work=unit_of_work,
        repository=repository,
        dispatcher=dispatcher,
        metrics=metrics,
        batch_size=10,
        retry_countdown_seconds=30,
        stop_requested=lambda: False,
        known_dispatchers=KNOWN_DISPATCHERS,
        logger=logging.getLogger("scafold"),
        clock=time.monotonic,
    )
    result: DrainResult = run(drain.execute())
    return result


@then(parsers.parse('a mensagem está "{status}"'))
def _(queued: QueuedMessage, status: str) -> None:
    assert queued.status == status


@then(parsers.parse('a mensagem está "{status}" com {attempts:d} tentativas'))
def _(queued: QueuedMessage, status: str, attempts: int) -> None:
    assert (queued.status, queued.attempts) == (status, attempts)


@then(parsers.parse('a falha registrada é "{kind}"'))
def _(repository: InMemoryOutboxRepository, kind: str) -> None:
    assert [failure.kind for failure in repository.failures] == [kind]


@then(parsers.parse('a métrica de mortas registrou o motivo "{reason}"'))
def _(metrics: RecordingOutboxMetrics, reason: str) -> None:
    assert [dead_reason for _, _, dead_reason in metrics.dead] == [reason]


@then(
    parsers.parse(
        "o ciclo publicou {published:d}, reagendou {retried:d} e matou {dead:d} mensagens"
    )
)
def _(outcome: DrainResult, published: int, retried: int, dead: int) -> None:
    assert (outcome.published, outcome.retried, outcome.dead) == (published, retried, dead)


@then(parsers.parse('o backlog publicado é zero para "{dispatcher}"'))
def _(metrics: RecordingOutboxMetrics, dispatcher: str) -> None:
    assert metrics.backlogs == [{dispatcher: (0, 0.0)}]


@then(parsers.parse('a transação "{name}" commitou'))
def _(unit_of_work: FakeUnitOfWork, name: str) -> None:
    assert unit_of_work.committed == [name]

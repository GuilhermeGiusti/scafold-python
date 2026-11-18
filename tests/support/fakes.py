"""Fakes da suíte. Código normal, sem framework de mock.

``FakeUnitOfWork``, ``InMemoryExampleRepository``, ``InMemoryExampleReader`` e
``InMemoryIntegrationWriter`` formam um conjunto coerente sobre o mesmo ``InMemoryStore``: o que é
gravado dentro da transação some se o bloco levanta, e gravar fora dela é recusado. É o que deixa o
fake passar pelo mesmo teste de contrato que o adaptador SQL.
"""

from __future__ import annotations

import copy
from collections.abc import AsyncIterator, Iterable, Mapping
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass, field, replace
from typing import Literal
from uuid import UUID, uuid4

from scafold.applications.ports.outbox_metrics import DeathReason, DispatchResult
from scafold.applications.queries.example_summary import ExampleSummary
from scafold.domain.bounded_context_example.aggregates.example import Example
from scafold.domain.bounded_context_example.errors.label_taken import LabelTaken
from scafold.domain.bounded_context_example.value_objects.category import Category
from scafold.domain.bounded_context_example.value_objects.example_id import ExampleId
from scafold.domain.outbox.dispatchers import RABBITMQ_DISPATCHER
from scafold.domain.outbox.errors.no_pending_message import NoPendingMessage
from scafold.domain.outbox.value_objects.backlog_entry import BacklogEntry
from scafold.domain.outbox.value_objects.dispatch_outcome import DispatchOutcome
from scafold.domain.outbox.value_objects.failure import Failure
from scafold.domain.outbox.value_objects.integration_event import IntegrationEvent, validate
from scafold.domain.outbox.value_objects.pending_message import PendingMessage
from scafold.domain.shared.aggregates.aggregate_root import AggregateRoot
from scafold.domain.shared.events.event_base import IDomainEvent
from scafold.infrastructure.observability.use_case_metrics import UseCaseStatus
from scafold.infrastructure.persistence.unit_of_work import OutsideUnitOfWork

# ---------------------------------------------------------------------------------------------
# Camada de dados
# ---------------------------------------------------------------------------------------------


@dataclass
class InMemoryStore:
    """O "banco" dos fakes."""

    examples: dict[ExampleId, Example] = field(default_factory=dict)
    integration_events: list[IntegrationEvent] = field(default_factory=list)


class FakeUnitOfWork:
    """Implementa ``IUnitOfWork`` sobre o ``InMemoryStore``.

    A transação externa tira uma cópia do store e a devolve se o bloco levantar: é o rollback. A
    aninhada participa. ``opened`` e ``committed`` guardam os nomes, para o teste conferir.
    """

    def __init__(self, store: InMemoryStore | None = None) -> None:
        self.store = store if store is not None else InMemoryStore()
        self.opened: list[str] = []
        self.committed: list[str] = []
        self._depth = 0

    def in_transaction(self) -> bool:
        return self._depth > 0

    def transaction(self, name: str) -> AbstractAsyncContextManager[None]:
        return self._open(name)

    @asynccontextmanager
    async def _open(self, name: str) -> AsyncIterator[None]:
        if self._depth > 0:
            self._depth += 1
            try:
                yield
            finally:
                self._depth -= 1
            return

        self.opened.append(name)
        snapshot = copy.deepcopy((self.store.examples, self.store.integration_events))
        self._depth = 1
        try:
            yield
        except BaseException:
            self.store.examples, self.store.integration_events = snapshot
            raise
        finally:
            self._depth = 0
        self.committed.append(name)

    def require_transaction(self, who: str) -> None:
        if not self.in_transaction():
            raise OutsideUnitOfWork(f"{who} pediu escrita fora de uma Unit of Work")


class InMemoryExampleRepository:
    """Implementa ``IExampleRepository`` com a unicidade do nome e a recusa fora da transação."""

    def __init__(self, unit_of_work: FakeUnitOfWork) -> None:
        self._uow = unit_of_work

    async def add(self, example: Example) -> None:
        self._uow.require_transaction("example_repository")
        examples = self._uow.store.examples
        if any(stored.label == example.label for stored in examples.values()):
            raise LabelTaken("o nome ja pertence a outro example")
        examples[example.id] = _stored(example)

    async def get(self, example_id: ExampleId) -> Example | None:
        stored = self._uow.store.examples.get(example_id)
        return None if stored is None else _stored(stored)

    async def save(self, example: Example) -> None:
        self._uow.require_transaction("example_repository")
        stored = self._uow.store.examples[example.id]
        stored.archived_at = example.archived_at

    async def remove_archived(self) -> int:
        self._uow.require_transaction("example_repository")
        examples = self._uow.store.examples
        archived = [example_id for example_id, stored in examples.items() if stored.is_archived]
        for example_id in archived:
            del examples[example_id]
        return len(archived)


def _stored(example: Example) -> Example:
    """O que volta do "banco": uma cópia sem os eventos, como o reconstruído pelo mapper."""
    copied = copy.deepcopy(example)
    copied.clear_events()
    return copied


class InMemoryExampleReader:
    """Implementa ``IExampleReader`` sobre o store."""

    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def list_summaries(self, *, limit: int) -> list[ExampleSummary]:
        ordered = sorted(self._store.examples.values(), key=lambda example: example.label)
        return [
            ExampleSummary(
                id=example.id,
                label=example.label,
                item_count=len(example.items),
                archived=example.is_archived,
            )
            for example in ordered[:limit]
        ]


class InMemoryIntegrationWriter:
    """Implementa ``IIntegrationWriter`` gravando no store, dentro da transação do fake."""

    def __init__(self, unit_of_work: FakeUnitOfWork) -> None:
        self._uow = unit_of_work

    async def write(self, event: IntegrationEvent) -> UUID:
        validate(event)
        self._uow.require_transaction("outbox_writer")
        self._uow.store.integration_events.append(event)
        return uuid4()


# ---------------------------------------------------------------------------------------------
# Portas da aplicação e do domínio
# ---------------------------------------------------------------------------------------------


class KeywordCategoryGateway:
    """Implementa ``ICategoryGateway`` como o fornecedor de mentira: "premium" no nome é premium."""

    async def classify(self, label: str) -> Category:
        return Category.PREMIUM if "premium" in label.lower() else Category.STANDARD


class RecordingDomainEventDispatcher:
    """Implementa ``IDomainEventDispatcher`` em memória: guarda o que despachou."""

    def __init__(self) -> None:
        self.dispatched: list[IDomainEvent] = []

    def collect[IdT](self, aggregate: AggregateRoot[IdT]) -> set[IDomainEvent]:
        events = set(aggregate.get_uncommitted_events())
        aggregate.clear_events()
        return events

    def dispatch(self, events: Iterable[IDomainEvent]) -> None:
        self.dispatched.extend(events)


# ---------------------------------------------------------------------------------------------
# Métricas
# ---------------------------------------------------------------------------------------------


@dataclass
class RecordingUseCaseMetrics:
    executions: list[tuple[str, UseCaseStatus, str]] = field(default_factory=list)

    def use_case_executed(
        self, *, use_case: str, status: UseCaseStatus, error_type: str, duration_seconds: float
    ) -> None:
        self.executions.append((use_case, status, error_type))


@dataclass
class RecordingDomainEventMetrics:
    """Implementa ``IDomainEventMetrics`` guardando cada medição."""

    published_events: list[str] = field(default_factory=list)
    handled_events: list[tuple[str, str, str]] = field(default_factory=list)

    def published(self, *, event_name: str) -> None:
        self.published_events.append(event_name)

    def handled(
        self,
        *,
        event_name: str,
        handler: str,
        status: Literal["ok", "error"],
        duration_seconds: float,
    ) -> None:
        self.handled_events.append((event_name, handler, status))


@dataclass
class RecordingTranslationErrorMetrics:
    failures: list[str] = field(default_factory=list)

    def translation_failed(self, *, gateway: str) -> None:
        self.failures.append(gateway)


@dataclass
class RecordingOutboxMetrics:
    attempts: list[tuple[str, str, DispatchResult]] = field(default_factory=list)
    dead: list[tuple[str, str, DeathReason]] = field(default_factory=list)
    backlogs: list[dict[str, tuple[int, float]]] = field(default_factory=list)
    durations: list[float] = field(default_factory=list)
    written: list[str] = field(default_factory=list)

    def record_attempt(self, *, event: str, destination: str, result: DispatchResult) -> None:
        self.attempts.append((event, destination, result))

    def record_dead(self, *, event: str, destination: str, reason: DeathReason) -> None:
        self.dead.append((event, destination, reason))

    def record_backlog(self, backlog: Mapping[str, tuple[int, float]]) -> None:
        self.backlogs.append(dict(backlog))

    def record_drain_duration(self, seconds: float) -> None:
        self.durations.append(seconds)

    def record_event_written(self, *, event: str) -> None:
        self.written.append(event)


# ---------------------------------------------------------------------------------------------
# Outbox
# ---------------------------------------------------------------------------------------------


@dataclass
class QueuedMessage:
    """Uma linha da fila em memória."""

    message: PendingMessage
    status: Literal["PENDING", "PUBLISHED", "DEAD"] = "PENDING"
    attempts: int = 0
    available: bool = True


class InMemoryOutboxRepository:
    """Implementa ``IOutboxRepository`` sobre uma lista, com a máquina de estados da tabela."""

    def __init__(self, unit_of_work: FakeUnitOfWork) -> None:
        self._uow = unit_of_work
        self.queue: list[QueuedMessage] = []
        self.failures: list[Failure] = []

    def enqueue(self, message: PendingMessage) -> QueuedMessage:
        queued = QueuedMessage(message=message, attempts=message.attempts)
        self.queue.append(queued)
        return queued

    async def claim_next_pending(self, dispatcher: str) -> PendingMessage:
        self._uow.require_transaction("outbox_repository")
        for queued in self.queue:
            if queued.status == "PENDING" and queued.available:
                return replace(queued.message, attempts=queued.attempts)
        raise NoPendingMessage()

    async def mark_published(self, message_id: UUID) -> None:
        self._find(message_id).status = "PUBLISHED"

    async def mark_dead(self, message_id: UUID) -> None:
        queued = self._find(message_id)
        queued.status = "DEAD"
        queued.attempts += 1

    async def schedule_retry(self, message_id: UUID, countdown_seconds: int) -> None:
        queued = self._find(message_id)
        queued.attempts += 1
        queued.available = False

    async def record_failure(self, failure: Failure) -> None:
        self.failures.append(failure)

    async def backlog(self) -> list[BacklogEntry]:
        pending = [queued for queued in self.queue if queued.status == "PENDING"]
        if not pending:
            return []
        return [BacklogEntry(dispatcher=RABBITMQ_DISPATCHER, pending=len(pending), oldest_age_seconds=1.0)]

    def _find(self, message_id: UUID) -> QueuedMessage:
        [queued] = [queued for queued in self.queue if queued.message.id == message_id]
        return queued


class ScriptedDispatcher:
    """Implementa ``IDispatcher`` devolvendo um roteiro de resultados; repete o último."""

    def __init__(self, *outcomes: DispatchOutcome) -> None:
        self._outcomes = list(outcomes)
        self.seen: list[PendingMessage] = []

    @property
    def name(self) -> str:
        return RABBITMQ_DISPATCHER

    async def dispatch(self, message: PendingMessage) -> DispatchOutcome:
        self.seen.append(message)
        if len(self._outcomes) > 1:
            return self._outcomes.pop(0)
        return self._outcomes[0]

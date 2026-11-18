from datetime import UTC, datetime
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from scafold.applications.handlers.all_events_handler import AllEventsHandler
from scafold.applications.handlers.example_created_handler import ExampleCreatedHandler
from scafold.domain.bounded_context_example.aggregates.example import Example
from scafold.domain.bounded_context_example.events.example_created import ExampleCreated
from scafold.domain.bounded_context_example.value_objects.category import Category
from scafold.domain.shared.events.event_base import IDomainEvent
from scafold.infrastructure.events.event_dispatcher import DomainEventDispatcher
from scafold.infrastructure.events.event_manager import DomainEventManager

from ..support.fakes import RecordingDomainEventMetrics

scenarios("infrastructure/domain_events.feature")


class FailingHandler:
    """Handler que falha sempre, como um envio que caiu."""

    def listener_to(self) -> list[type[IDomainEvent]]:
        return [ExampleCreated]

    def handle(self, event: IDomainEvent) -> None:
        raise RuntimeError("canal fora do ar")


@pytest.fixture
def metrics() -> RecordingDomainEventMetrics:
    return RecordingDomainEventMetrics()


@pytest.fixture
def notifications() -> list[str]:
    return []


@pytest.fixture
def records() -> list[dict[str, Any]]:
    return []


@pytest.fixture
def manager(metrics: RecordingDomainEventMetrics) -> DomainEventManager:
    return DomainEventManager(metrics=metrics)


def register_process_handlers(
    manager: DomainEventManager, notifications: list[str], records: list[dict[str, Any]]
) -> None:
    manager.register(ExampleCreatedHandler(notifications.append), AllEventsHandler(records.append))


@given("os handlers do processo registrados")
def _(manager: DomainEventManager, notifications: list[str], records: list[dict[str, Any]]) -> None:
    register_process_handlers(manager, notifications, records)


@given("um handler que falha registrado antes dos handlers do processo")
def _(manager: DomainEventManager, notifications: list[str], records: list[dict[str, Any]]) -> None:
    manager.register(FailingHandler())
    register_process_handlers(manager, notifications, records)


@when(parsers.parse('o Example "{label}" criado é despachado'))
def _(metrics: RecordingDomainEventMetrics, label: str) -> None:
    example = Example.create(label=label, category=Category.STANDARD, now=datetime.now(UTC))
    dispatcher = DomainEventDispatcher(metrics=metrics)
    dispatcher.dispatch(dispatcher.collect(example))


@then(parsers.parse('o handler da criação avisou "{text}"'))
def _(notifications: list[str], text: str) -> None:
    [notification] = notifications
    assert text in notification


@then(parsers.parse('o handler de todos os eventos registrou "{name}"'))
def _(records: list[dict[str, Any]], name: str) -> None:
    assert [record["name"] for record in records] == [name]


@then(parsers.parse('a publicação de "{name}" foi contada'))
def _(metrics: RecordingDomainEventMetrics, name: str) -> None:
    assert metrics.published_events == [name]


@then(parsers.parse('o tratamento de "{handler}" foi medido como "{status}"'))
def _(metrics: RecordingDomainEventMetrics, handler: str, status: str) -> None:
    assert [
        recorded for _, name, recorded in metrics.handled_events if name == handler
    ] == [status]

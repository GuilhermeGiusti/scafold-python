import logging
from uuid import UUID

import pytest
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode
from pytest_bdd import parsers, scenarios, then, when

from scafold.applications.commands.create_example_command import CreateExampleCommand
from scafold.applications.shared.use_case import NullaryUseCase
from scafold.bootstrap.composition import LOGGER_NAME
from scafold.domain.bounded_context_example.errors.invalid_label import InvalidLabel
from scafold.infrastructure.observability.observed_use_cases import ObservedNullaryUseCase
from scafold.infrastructure.observability.use_case_observer import UseCaseObserver

from ..conftest import Run
from ..support.fakes import RecordingUseCaseMetrics
from ..support.scene import Scene, build_scene

scenarios("infrastructure/use_case_observation.feature")


@pytest.fixture
def traced_scene(tracer_provider: TracerProvider) -> Scene:
    return build_scene(tracer_provider=tracer_provider)


def span_named(spans: InMemorySpanExporter, name: str) -> ReadableSpan:
    [span] = [span for span in spans.get_finished_spans() if span.name == name]
    return span


@when(parsers.parse('a borda cria o Example "{label}"'), target_fixture="outcome")
def _(run: Run, traced_scene: Scene, label: str) -> UUID | InvalidLabel:
    try:
        example_id: UUID = run(
            traced_scene.use_cases.create_example.execute(CreateExampleCommand(label=label))
        )
    except InvalidLabel as error:
        return error
    return example_id


class CountItemsUseCase(NullaryUseCase[int]):
    """Um use case síncrono mínimo, só para exercitar o decorator do contrato sem ``Async``."""

    def execute(self) -> int:
        return 3


@pytest.fixture
def sync_metrics() -> RecordingUseCaseMetrics:
    return RecordingUseCaseMetrics()


@when(parsers.parse('a borda executa um use case síncrono rotulado "{use_case}"'))
def _(tracer_provider: TracerProvider, sync_metrics: RecordingUseCaseMetrics, use_case: str) -> None:
    observer = UseCaseObserver(
        metrics=sync_metrics, logger=logging.getLogger(LOGGER_NAME), tracer_provider=tracer_provider
    )
    observed = ObservedNullaryUseCase(CountItemsUseCase(), use_case=use_case, observer=observer)
    assert observed.execute() == 3


@then(parsers.parse('o decorator síncrono mediu "{use_case}" como "{status}"'))
def _(sync_metrics: RecordingUseCaseMetrics, use_case: str, status: str) -> None:
    assert sync_metrics.executions == [(use_case, status, "none")]


@then(
    parsers.parse(
        'a execução de "{use_case}" foi medida como "{status}" com o erro "{error_type}"'
    )
)
def _(traced_scene: Scene, use_case: str, status: str, error_type: str) -> None:
    assert traced_scene.use_case_metrics.executions == [(use_case, status, error_type)]


@then(parsers.parse('o span "{name}" foi aberto com o status "{status}"'))
def _(spans: InMemorySpanExporter, name: str, status: str) -> None:
    span = span_named(spans, name)
    assert span.attributes is not None
    assert span.attributes["status"] == status
    assert span.status.status_code is not StatusCode.ERROR


@then(parsers.parse('o span "{name}" não existe, porque a Unit of Work é o fake'))
def _(spans: InMemorySpanExporter, name: str) -> None:
    assert name not in {span.name for span in spans.get_finished_spans()}


@then(parsers.parse('o span "{name}" saiu como erro com a descrição "{description}"'))
def _(spans: InMemorySpanExporter, name: str, description: str) -> None:
    span = span_named(spans, name)
    assert (span.status.status_code, span.status.description) == (StatusCode.ERROR, description)


@then(parsers.parse('o span "{name}" não tem eventos de exceção'))
def _(spans: InMemorySpanExporter, name: str) -> None:
    assert span_named(spans, name).events == ()

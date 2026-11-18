import logging

import pytest
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from pytest_bdd import given, parsers, scenarios, then, when

from scafold.applications.ports.outbox_metrics import RESULT_PUBLISHED
from scafold.bootstrap.composition import LOGGER_NAME, MetricsAdapters, build_metrics_adapters

scenarios("infrastructure/metrics_adapters.feature")


@pytest.fixture
def reader() -> InMemoryMetricReader:
    return InMemoryMetricReader()


@given("as métricas do processo ligadas", target_fixture="adapters")
def _(reader: InMemoryMetricReader) -> MetricsAdapters:
    provider = MeterProvider(metric_readers=[reader])
    return build_metrics_adapters(provider, logging.getLogger(LOGGER_NAME))


@given("as métricas do processo desligadas", target_fixture="adapters")
def _() -> MetricsAdapters:
    return build_metrics_adapters(None, logging.getLogger(LOGGER_NAME))


@when("um use case termina")
def _(adapters: MetricsAdapters) -> None:
    adapters.use_case.use_case_executed(
        use_case="create_example", status="ok", error_type="none", duration_seconds=0.01
    )


@when("uma transação termina")
def _(adapters: MetricsAdapters) -> None:
    adapters.persistence.transaction_finished(
        transaction="create_example", status="committed", error_type="none", duration_seconds=0.01
    )


@when("um evento de domínio é publicado")
def _(adapters: MetricsAdapters) -> None:
    adapters.domain_events.published(event_name="bounded_context_example.example.created")


@when("um erro de tradução é contado")
def _(adapters: MetricsAdapters) -> None:
    adapters.translation.translation_failed(gateway="category_gateway")


@when("uma tentativa de entrega é registrada")
def _(adapters: MetricsAdapters) -> None:
    adapters.outbox.record_attempt(
        event="example.created", destination="example", result=RESULT_PUBLISHED
    )


@then(parsers.parse('o leitor de métricas recebe o instrumento "{name}"'))
def _(reader: InMemoryMetricReader, name: str) -> None:
    data = reader.get_metrics_data()
    assert data is not None
    names = {
        metric.name
        for resource in data.resource_metrics
        for scope in resource.scope_metrics
        for metric in scope.metrics
    }
    assert name in names, names


@then(parsers.parse('o log recebe em DEBUG "{line}"'))
def _(caplog: pytest.LogCaptureFixture, line: str) -> None:
    debug = [r.getMessage() for r in caplog.records if r.levelno == logging.DEBUG]
    assert line in debug


@pytest.fixture(autouse=True)
def _debug_capture(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)

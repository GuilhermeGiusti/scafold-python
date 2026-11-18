from uuid import uuid4

from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode, format_trace_id
from pytest_bdd import given, parsers, scenarios, then, when

from scafold.domain.outbox.dispatchers import RABBITMQ_DISPATCHER
from scafold.domain.outbox.value_objects.dispatch_outcome import DispatchOutcome
from scafold.domain.outbox.value_objects.pending_message import PendingMessage
from scafold.domain.outbox.value_objects.permanent_failure import PermanentFailure
from scafold.domain.outbox.value_objects.published import Published
from scafold.infrastructure.observability.traced_dispatcher import (
    DISPATCH_SPAN_ATTRIBUTES,
    TracedDispatcher,
)

from ..conftest import Run
from ..support.fakes import ScriptedDispatcher

scenarios("infrastructure/traced_dispatcher.feature")


def dispatch_span(spans: InMemorySpanExporter) -> ReadableSpan:
    [span] = [span for span in spans.get_finished_spans() if span.name.startswith("outbox.")]
    return span


@given(
    parsers.parse('uma mensagem gravada dentro do trace "{trace_id}"'), target_fixture="message"
)
def _(trace_id: str) -> PendingMessage:
    return PendingMessage(
        id=uuid4(),
        destination="example",
        event_type="example.created",
        event_version=1,
        payload={"id": "1"},
        aggregate_type="example",
        aggregate_id="1",
        correlation_id=trace_id,
        trace_context=f"00-{trace_id}-00f067aa0ba902b7-01",
        dispatcher=RABBITMQ_DISPATCHER,
        attempts=0,
        routing_key="example.created",
    )


@given("a Strategy aceitando a publicação", target_fixture="strategy")
def _() -> ScriptedDispatcher:
    return ScriptedDispatcher(Published())


@given(
    parsers.parse('a Strategy falhando de forma permanente com o detalhe "{detail}"'),
    target_fixture="strategy",
)
def _(detail: str) -> ScriptedDispatcher:
    return ScriptedDispatcher(PermanentFailure(detail))


@when("o envoltório envia a mensagem", target_fixture="outcome")
def _(
    run: Run, tracer_provider: TracerProvider, strategy: ScriptedDispatcher, message: PendingMessage
) -> DispatchOutcome:
    traced = TracedDispatcher(strategy, tracer_provider=tracer_provider)
    outcome: DispatchOutcome = run(traced.dispatch(message))
    return outcome


@then(parsers.parse('o span "{name}" pertence ao trace "{trace_id}"'))
def _(spans: InMemorySpanExporter, name: str, trace_id: str) -> None:
    span = dispatch_span(spans)
    assert span.name == name
    assert format_trace_id(span.context.trace_id) == trace_id


@then("o span de envio tem exatamente os atributos do contrato")
def _(spans: InMemorySpanExporter) -> None:
    attributes = dispatch_span(spans).attributes
    assert attributes is not None
    assert sorted(attributes) == sorted(DISPATCH_SPAN_ATTRIBUTES)


@then(parsers.parse('o span de envio saiu como erro com a descrição "{description}"'))
def _(spans: InMemorySpanExporter, description: str) -> None:
    status = dispatch_span(spans).status
    assert (status.status_code, status.description) == (StatusCode.ERROR, description)


@then(parsers.parse('"{detail}" não aparece no span de envio'))
def _(spans: InMemorySpanExporter, detail: str) -> None:
    span = dispatch_span(spans)
    assert detail not in span.to_json()

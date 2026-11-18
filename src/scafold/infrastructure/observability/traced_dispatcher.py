"""O envoltório que abre o span de cada envio da outbox (emenda da ADR-006).

Cumpre ``IDispatcher`` e envolve a Strategy, na montagem do job. A drenagem é um use case e não
importa a biblioteca de telemetria; a Strategy nunca abre span. O span fica aqui, por fora das duas.

**O span continua o trace do produtor**, a partir do ``traceparent`` gravado na linha: o envio
aparece no trace de quem gravou o evento, na fronteira assíncrona em que o trace se perderia.

**``message_id`` e ``correlation_id`` são atributos de span**, e isso é permitido; proibido é usá-los
como rótulo de métrica (ADR-012).

**Numa falha, o status leva só o tipo do resultado**, nunca o detalhe: o detalhe traz a mensagem do
broker, e mensagem de erro não vai para sinal. Ele fica no histórico ``outbox_error``.
"""

from __future__ import annotations

from typing import assert_never

from opentelemetry.trace import SpanKind, Status, StatusCode, TracerProvider
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from scafold.domain.outbox.ports.dispatcher import IDispatcher
from scafold.domain.outbox.value_objects.dispatch_outcome import DispatchOutcome
from scafold.domain.outbox.value_objects.pending_message import PendingMessage
from scafold.domain.outbox.value_objects.permanent_failure import PermanentFailure
from scafold.domain.outbox.value_objects.published import Published
from scafold.domain.outbox.value_objects.transient_failure import TransientFailure
from scafold.infrastructure.observability.opentelemetry_outbox_metrics import (
    INSTRUMENTATION_SCOPE,
)

#: Os atributos do contrato. Nunca payload nem detalhe de erro.
DISPATCH_SPAN_ATTRIBUTES = (
    "event",
    "destination",
    "dispatcher",
    "attempts",
    "message_id",
    "correlation_id",
)

_propagator = TraceContextTextMapPropagator()


def dispatch_span_name(event_type: str) -> str:
    return f"outbox.dispatch {event_type}"


class TracedDispatcher:
    """Implementa ``IDispatcher``, abrindo ``outbox.dispatch <evento>`` em volta do envio."""

    def __init__(self, inner: IDispatcher, *, tracer_provider: TracerProvider) -> None:
        self._inner = inner
        self._tracer = tracer_provider.get_tracer(INSTRUMENTATION_SCOPE)

    @property
    def name(self) -> str:
        return self._inner.name

    async def dispatch(self, message: PendingMessage) -> DispatchOutcome:
        parent = (
            _propagator.extract({"traceparent": message.trace_context})
            if message.trace_context
            else None
        )
        with self._tracer.start_as_current_span(
            dispatch_span_name(message.event_type),
            context=parent,
            kind=SpanKind.PRODUCER,
            attributes={
                "event": message.event_type,
                "destination": message.destination,
                "dispatcher": self._inner.name,
                "attempts": message.attempts,
                "message_id": str(message.id),
                "correlation_id": message.correlation_id,
            },
            # A Strategy nunca lança; se lançasse, a mensagem da exceção não iria para o span.
            record_exception=False,
            set_status_on_exception=False,
        ) as span:
            outcome = await self._inner.dispatch(message)
            match outcome:
                case Published():
                    span.set_status(Status(StatusCode.OK))
                case TransientFailure():
                    span.set_status(Status(StatusCode.ERROR, "transient_error"))
                case PermanentFailure():
                    span.set_status(Status(StatusCode.ERROR, "permanent_error"))
                case _:
                    assert_never(outcome)
            return outcome

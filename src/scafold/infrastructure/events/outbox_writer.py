"""O gravador da outbox: grava o evento de integração na transação de quem chamou (ADR-006).

O produtor chama ``write`` dentro da transação da Unit of Work que grava o estado. O commit grava o
estado e o evento juntos; um rollback não deixa nenhum dos dois.

**Ele não publica.** Não há Strategy aqui, e é isso que torna o dual write impossível por
construção: a publicação é exclusivamente do job da outbox.

**A ordem das recusas é o contrato.** O evento é validado e o span corrente é conferido antes de
pedir a conexão. Fora de transação, quem recusa é a própria Unit of Work, com
``OutsideUnitOfWork``, e o gravador deixa a recusa subir como veio.

**O ``correlation_id`` e o ``traceparent`` vêm do contexto, nunca de parâmetro.** Os dois saem do
span corrente: o identificador de correlação É o id do trace.

**O carimbo é obrigatório.** Vem de ``OUTBOX_DISPATCHER``, lido pela configuração e entregue pela
montagem. Os dados de envio da Strategy carimbada ficam congelados na tabela auxiliar.
"""

from __future__ import annotations

import json
import uuid

from opentelemetry import trace
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from scafold.applications.ports.outbox_metrics import IOutboxMetrics
from scafold.domain.outbox.dispatchers import KNOWN_DISPATCHERS
from scafold.domain.outbox.errors.missing_trace_context import MissingTraceContext
from scafold.domain.outbox.errors.unknown_dispatcher import UnknownDispatcher
from scafold.domain.outbox.value_objects.integration_event import IntegrationEvent, validate
from scafold.infrastructure.persistence.outbox.sqlc import outbox
from scafold.infrastructure.persistence.unit_of_work import UnitOfWork

#: O nome de quem pede a conexão, rótulo `repository` da medição de queries.
WRITER_NAME = "outbox_writer"

_propagator = TraceContextTextMapPropagator()


class OutboxWriter:
    """Implementa ``IIntegrationWriter``. Construído uma vez, na montagem do processo que grava.

    Recebe a ``UnitOfWork`` concreta, e não a porta: ``write_querier`` devolve uma conexão do driver
    e por isso fica fora da porta.
    """

    def __init__(
        self, *, dispatcher: str, unit_of_work: UnitOfWork, metrics: IOutboxMetrics
    ) -> None:
        if dispatcher not in KNOWN_DISPATCHERS:
            raise UnknownDispatcher()
        self._dispatcher = dispatcher
        self._unit_of_work = unit_of_work
        self._metrics = metrics

    async def write(self, event: IntegrationEvent) -> uuid.UUID:
        validate(event)
        span_context = trace.get_current_span().get_span_context()
        if not span_context.is_valid:
            raise MissingTraceContext()

        async with self._unit_of_work.write_querier(WRITER_NAME) as connection:
            querier = outbox.AsyncQuerier(connection)
            written = await querier.insert_outbox_message(
                outbox.InsertOutboxMessageParams(
                    destination=event.destination,
                    event_type=event.event_type,
                    event_version=event.event_version,
                    # `payload` é `jsonb`, e o gerador o tipa como `Any`. Vai a string JSON já
                    # serializada, que é o que o codec de `jsonb` do dialeto asyncpg espera.
                    payload=json.dumps(event.payload, ensure_ascii=False),
                    aggregate_type=event.aggregate_type,
                    aggregate_id=event.aggregate_id,
                    correlation_id=trace.format_trace_id(span_context.trace_id),
                    trace_context=_traceparent(),
                    dispatcher=self._dispatcher,
                )
            )
            # `:one` devolve `Optional`; um INSERT com RETURNING sempre devolve a linha.
            assert written is not None
            message_id = written.id
            # Valor congelado: o envio nunca o recalcula.
            await querier.insert_outbox_message_rabbitmq(
                message_id=message_id, routing_key=event.routing_key or event.event_type
            )

        self._metrics.record_event_written(event=event.event_type)
        return message_id


def _traceparent() -> str | None:
    """O ``traceparent`` W3C do span corrente, para o envio continuar o trace do produtor."""
    carrier: dict[str, str] = {}
    _propagator.inject(carrier)
    return carrier.get("traceparent")

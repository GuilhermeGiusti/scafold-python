"""Os spans da camada de dados: um por transação externa e um por query gerada pelo sqlc.

Usam os mesmos nomes do catálogo de métricas. Quem vê
``db_transaction_duration_seconds{transaction="create_example"}`` alto abre o trace e encontra o
span ``db.transaction create_example``, com as queries dele por baixo.

**Só nomes fixos entram no span.** Texto do SQL, parâmetro de query, id e mensagem de exceção nunca
viram nome, atributo, evento nem descrição de status. Da exceção sai apenas o nome da classe.
"""

from __future__ import annotations

from opentelemetry.trace import NoOpTracerProvider, Span, Status, StatusCode, Tracer, TracerProvider

from scafold.infrastructure.persistence.metrics.opentelemetry_persistence_metrics import (
    INSTRUMENTATION_SCOPE,
)

#: Os atributos do contrato do span de transação. São os rótulos de `db_transactions_total`.
TRANSACTION_SPAN_ATTRIBUTES = ("transaction", "status", "error_type")

#: Os atributos do contrato do span de query. São os rótulos de `db_query_duration_seconds`.
QUERY_SPAN_ATTRIBUTES = ("repository", "query", "transaction", "status")


def persistence_tracer(tracer_provider: TracerProvider | None) -> Tracer:
    """O tracer da camada de dados. Provider vazio é no-op, e nunca o global."""
    provider = tracer_provider if tracer_provider is not None else NoOpTracerProvider()
    return provider.get_tracer(INSTRUMENTATION_SCOPE)


def transaction_span_name(transaction: str) -> str:
    return f"db.transaction {transaction}"


def query_span_name(query: str) -> str:
    return f"db.query {query}"


def mark_failed(span: Span, error_type: str) -> None:
    """Marca o span como erro levando só o nome da classe da exceção, nunca a mensagem."""
    span.set_status(Status(StatusCode.ERROR, error_type))

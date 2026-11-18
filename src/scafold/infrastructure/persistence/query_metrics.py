"""Mede cada query gerada pelo sqlc, sem tocar no código gerado nem no repositório.

Toda query que o sqlc emite começa com o comentário ``-- name: <query> :<tipo>``. Um ouvinte de
eventos do SQLAlchemy lê esse nome antes da execução, mede o tempo até o fim e rotula a medição com
o repositório e a transação que estão nas ``ContextVar`` da Unit of Work.

O mesmo ouvinte abre o span ``db.query <query>``, filho do span da transação, ou de quem estiver
aberto quando a query roda fora de uma Unit of Work. SQL que não veio do sqlc não é medido nem ganha
span: ele não tem nome estável para virar rótulo.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from typing import Any

from opentelemetry.trace import Span, SpanKind, TracerProvider
from sqlalchemy import event
from sqlalchemy.engine import Connection, ExceptionContext
from sqlalchemy.ext.asyncio import AsyncEngine

from scafold.infrastructure.persistence.metrics.persistence_metrics import (
    IPersistenceMetrics,
    QueryStatus,
)
from scafold.infrastructure.persistence.persistence_spans import (
    mark_failed,
    persistence_tracer,
    query_span_name,
)
from scafold.infrastructure.persistence.unit_of_work import (
    current_repository,
    current_transaction,
)

#: O comentário que o sqlc-gen-python põe na primeira linha de toda query gerada.
_SQLC_NAME = re.compile(r"^\s*-- name: (\w+)")

#: O repositório de uma query executada por uma conexão que não veio de `querier(...)`.
UNKNOWN_REPOSITORY = "unknown"

_STARTED_KEY = "query_metrics_started"
_SPAN_KEY = "query_metrics_span"


def query_name(statement: str) -> str | None:
    """O nome da query sqlc no início do SQL, ou ``None`` se o SQL não veio do sqlc."""
    match = _SQLC_NAME.match(statement)
    return match.group(1) if match else None


def instrument_queries(
    engine: AsyncEngine,
    metrics: IPersistenceMetrics,
    clock: Callable[[], float] = time.perf_counter,
    tracer_provider: TracerProvider | None = None,
) -> None:
    """Registra os ouvintes no engine. Chame uma vez, na montagem do processo."""
    tracer = persistence_tracer(tracer_provider)

    def before(
        conn: Connection,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        name = query_name(statement)
        if name is None:
            return
        conn.info[_STARTED_KEY] = clock()
        # O span leva o nome da query, e nunca o SQL nem os parâmetros dela.
        conn.info[_SPAN_KEY] = tracer.start_span(
            query_span_name(name),
            kind=SpanKind.CLIENT,
            attributes={
                "repository": current_repository() or UNKNOWN_REPOSITORY,
                "query": name,
                "transaction": current_transaction(),
            },
        )

    def after(
        conn: Connection,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        record(conn, statement, "ok", None)

    def on_error(exception_context: ExceptionContext) -> None:
        conn = exception_context.connection
        statement = exception_context.statement
        if conn is not None and statement is not None:
            failure = exception_context.original_exception
            record(conn, statement, "error", type(failure).__name__)

    def record(
        conn: Connection, statement: str, status: QueryStatus, error_type: str | None
    ) -> None:
        name = query_name(statement)
        started: float | None = conn.info.pop(_STARTED_KEY, None)
        span: Span | None = conn.info.pop(_SPAN_KEY, None)
        if span is not None:
            span.set_attribute("status", status)
            if error_type is not None:
                mark_failed(span, error_type)
            span.end()
        if name is None or started is None:
            return
        metrics.query_executed(
            repository=current_repository() or UNKNOWN_REPOSITORY,
            query=name,
            transaction=current_transaction(),
            status=status,
            duration_seconds=clock() - started,
        )

    sync_engine = engine.sync_engine
    event.listen(sync_engine, "before_cursor_execute", before)
    event.listen(sync_engine, "after_cursor_execute", after)
    event.listen(sync_engine, "handle_error", on_error)

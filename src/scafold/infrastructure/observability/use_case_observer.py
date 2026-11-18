"""O que os oito decorators fazem em comum: medir, rastrear, registrar e relançar."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager

from opentelemetry.trace import NoOpTracerProvider, Status, StatusCode, TracerProvider

from scafold.infrastructure.observability.opentelemetry_use_case_metrics import (
    INSTRUMENTATION_SCOPE,
)
from scafold.infrastructure.observability.use_case_metrics import NO_ERROR, IUseCaseMetrics

#: Os atributos do contrato do span de use case. São os rótulos de `use_case_executions_total`.
USE_CASE_SPAN_ATTRIBUTES = ("use_case", "status", "error_type")


def use_case_span_name(use_case: str) -> str:
    return f"use_case {use_case}"


class UseCaseObserver:
    """Envolve UMA execução: span, log de início e de fim, métrica e log da exceção.

    É um ``contextmanager`` síncrono de propósito: serve aos decorators sync e async, porque o
    ``await`` do use case acontece dentro do bloco. A exceção nunca é engolida: ela é medida,
    registrada e relançada para a borda traduzir.

    O span ``use_case <nome>`` fica corrente durante a execução. Por isso o span da transação que o
    use case abre nasce como filho dele, e o log escrito dentro do bloco já sai com o id do trace.
    O ``tracer_provider`` é o do processo, injetado na montagem; vazio, é no-op, nunca o global.

    Início e fim saem em DEBUG, porque são rotina. A falha sai em ERROR, com a pilha.
    """

    def __init__(
        self,
        *,
        metrics: IUseCaseMetrics,
        logger: logging.Logger,
        tracer_provider: TracerProvider | None = None,
    ) -> None:
        self._metrics = metrics
        self._log = logger
        provider = tracer_provider if tracer_provider is not None else NoOpTracerProvider()
        self._tracer = provider.get_tracer(INSTRUMENTATION_SCOPE)

    @contextmanager
    def observe(self, use_case: str) -> Iterator[None]:
        # `record_exception=False`: o evento de exceção levaria a mensagem do erro, e erro de
        # domínio costuma citar o dado recusado. Do erro, o span leva só o nome da classe.
        with self._tracer.start_as_current_span(
            use_case_span_name(use_case),
            attributes={"use_case": use_case},
            record_exception=False,
            set_status_on_exception=False,
        ) as span:
            self._log.debug("use_case=%s event=started", use_case)
            started = time.perf_counter()
            try:
                yield
            except Exception as error:
                elapsed = time.perf_counter() - started
                error_type = type(error).__name__
                self._metrics.use_case_executed(
                    use_case=use_case,
                    status="error",
                    error_type=error_type,
                    duration_seconds=elapsed,
                )
                # Qualquer exceção marca o span como erro, esperada ou não: é a mesma regra do
                # `status="error"` da métrica.
                span.set_attribute("status", "error")
                span.set_attribute("error_type", error_type)
                span.set_status(Status(StatusCode.ERROR, error_type))
                self._log.exception("use_case=%s event=failed", use_case)
                raise
            elapsed = time.perf_counter() - started
            self._metrics.use_case_executed(
                use_case=use_case, status="ok", error_type=NO_ERROR, duration_seconds=elapsed
            )
            span.set_attribute("status", "ok")
            span.set_attribute("error_type", NO_ERROR)
            self._log.debug("use_case=%s event=finished duration=%.6f", use_case, elapsed)

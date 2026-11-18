"""Métricas de use case escritas no log."""

from __future__ import annotations

import logging

from scafold.infrastructure.observability.use_case_metrics import UseCaseStatus


class LoggingUseCaseMetrics:
    """Implementa ``IUseCaseMetrics`` escrevendo cada medição no log, em DEBUG, no formato que o
    Prometheus exporia. Serve para rodar sem coletor e com as métricas desligadas."""

    def __init__(self, logger: logging.Logger) -> None:
        self._log = logger

    def use_case_executed(
        self,
        *,
        use_case: str,
        status: UseCaseStatus,
        error_type: str,
        duration_seconds: float,
    ) -> None:
        self._log.debug(
            "use_case_executions_total{use_case=%s,status=%s,error_type=%s} +1",
            use_case,
            status,
            error_type,
        )
        self._log.debug(
            "use_case_duration_seconds{use_case=%s,status=%s} %.6f",
            use_case,
            status,
            duration_seconds,
        )

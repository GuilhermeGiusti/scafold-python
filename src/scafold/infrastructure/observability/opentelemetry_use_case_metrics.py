"""Métricas de use case com OpenTelemetry."""

from __future__ import annotations

from opentelemetry.metrics import Counter, Histogram, MeterProvider

from scafold.infrastructure.observability.use_case_metrics import UseCaseStatus

#: O escopo de instrumentação: o "dono" das métricas e dos spans de use case.
INSTRUMENTATION_SCOPE = "scafold.use_cases"

#: Limites do histograma, em segundos. O padrão do SDK foi pensado para milissegundos.
DURATION_BUCKETS_SECONDS = (
    0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0,
)


class OpenTelemetryUseCaseMetrics:
    """Implementa ``IUseCaseMetrics`` com instrumentos OpenTelemetry.

    O Prometheus publica ``use_case.executions`` como ``use_case_executions_total`` e
    ``use_case.duration`` como ``use_case_duration_seconds``, os nomes da porta.
    """

    def __init__(self, meter_provider: MeterProvider) -> None:
        meter = meter_provider.get_meter(INSTRUMENTATION_SCOPE)
        self._executions: Counter = meter.create_counter(
            "use_case.executions",
            unit="{execution}",
            description="Execucoes de use case encerradas, por status",
        )
        self._duration: Histogram = meter.create_histogram(
            "use_case.duration",
            unit="s",
            description="Duracao da execucao do use case",
            explicit_bucket_boundaries_advisory=DURATION_BUCKETS_SECONDS,
        )

    def use_case_executed(
        self,
        *,
        use_case: str,
        status: UseCaseStatus,
        error_type: str,
        duration_seconds: float,
    ) -> None:
        self._executions.add(1, {"use_case": use_case, "status": status, "error_type": error_type})
        self._duration.record(duration_seconds, {"use_case": use_case, "status": status})

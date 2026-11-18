"""Métrica de erro de tradução com OpenTelemetry."""

from __future__ import annotations

from opentelemetry.metrics import Counter, MeterProvider

#: O escopo de instrumentação dos adaptadores de serviço externo.
INSTRUMENTATION_SCOPE = "scafold.external"


class OpenTelemetryTranslationErrorMetrics:
    """Implementa ``ITranslationErrorMetrics``. O Prometheus publica
    ``external_translation_errors_total``."""

    def __init__(self, meter_provider: MeterProvider) -> None:
        meter = meter_provider.get_meter(INSTRUMENTATION_SCOPE)
        self._errors: Counter = meter.create_counter(
            "external.translation.errors",
            unit="{error}",
            description="Payloads do fornecedor que o mapper nao soube traduzir",
        )

    def translation_failed(self, *, gateway: str) -> None:
        self._errors.add(1, {"gateway": gateway})

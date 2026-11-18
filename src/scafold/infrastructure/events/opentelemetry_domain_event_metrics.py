"""Métricas de eventos de domínio com OpenTelemetry."""

from __future__ import annotations

from typing import Literal

from opentelemetry.metrics import Counter, Histogram, MeterProvider

#: O escopo de instrumentação: o "dono" das métricas no coletor.
INSTRUMENTATION_SCOPE = "scafold.domain_events"

#: Limites do histograma, em segundos. O padrão do SDK foi pensado para milissegundos.
DURATION_BUCKETS_SECONDS = (
    0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0,
)


class OpenTelemetryDomainEventMetrics:
    """Implementa ``IDomainEventMetrics`` com instrumentos OpenTelemetry.

    O Prometheus publica os nomes da porta: ``domain_events_published_total``,
    ``domain_event_handlers_total`` e ``domain_event_handler_duration_seconds``. O
    ``MeterProvider`` é o do processo e entra por construtor, nunca o global.
    """

    def __init__(self, meter_provider: MeterProvider) -> None:
        meter = meter_provider.get_meter(INSTRUMENTATION_SCOPE)
        self._published: Counter = meter.create_counter(
            "domain.events.published",
            unit="{event}",
            description="Eventos de dominio enviados aos handlers",
        )
        self._handlers: Counter = meter.create_counter(
            "domain.event.handlers",
            unit="{handling}",
            description="Tratamentos de evento encerrados, por status",
        )
        self._handler_duration: Histogram = meter.create_histogram(
            "domain.event.handler.duration",
            unit="s",
            description="Duracao de cada tratamento de evento",
            explicit_bucket_boundaries_advisory=DURATION_BUCKETS_SECONDS,
        )

    def published(self, *, event_name: str) -> None:
        self._published.add(1, {"event_name": event_name})

    def handled(
        self,
        *,
        event_name: str,
        handler: str,
        status: Literal["ok", "error"],
        duration_seconds: float,
    ) -> None:
        self._handlers.add(1, {"event_name": event_name, "handler": handler, "status": status})
        self._handler_duration.record(
            duration_seconds, {"event_name": event_name, "handler": handler}
        )

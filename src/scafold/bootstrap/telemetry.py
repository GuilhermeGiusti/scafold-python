"""A telemetria do processo: os providers de métricas e de traces, montados uma vez (ADR-012).

O processo envia os dois sinais por OTLP sobre HTTP para o endereço configurado. O que há atrás do
endereço (Prometheus e Jaeger direto, ou um Collector) é decisão de cada ambiente.

**Os providers entram por construtor em quem os usa, e nunca vêm do global.** A Unit of Work, o
observador de use case, o envoltório da outbox e o framework HTTP recebem os providers daqui.
"""

from __future__ import annotations

from dataclasses import dataclass

from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ALWAYS_ON

from scafold.bootstrap.settings import TelemetrySettings


@dataclass(frozen=True, slots=True, kw_only=True)
class Telemetry:
    """O que a montagem entrega a quem mede e a quem rastreia.

    ``meter_provider`` é ``None`` com as métricas desligadas: a montagem troca os adaptadores
    OpenTelemetry pelos de log. ``tracer_provider`` existe sempre: desligar os traces tira só o
    exportador, e os spans continuam dando o id do trace que vai em toda linha de log.
    """

    meter_provider: MeterProvider | None
    tracer_provider: TracerProvider

    def flush(self) -> None:
        """Envia agora o que está pendente, sem esperar o intervalo."""
        self.tracer_provider.force_flush()
        if self.meter_provider is not None:
            self.meter_provider.force_flush()

    def shutdown(self) -> None:
        """Envia o que falta e encerra. Uma vez, no encerramento do processo."""
        self.tracer_provider.shutdown()
        if self.meter_provider is not None:
            self.meter_provider.shutdown()


def build_telemetry(settings: TelemetrySettings) -> Telemetry:
    """Uma vez por processo. Montar não conecta: o primeiro envio é que abre a conexão."""
    resource = Resource.create({"service.name": settings.service_name})
    return Telemetry(
        meter_provider=_meter_provider(settings, resource),
        tracer_provider=_tracer_provider(settings, resource),
    )


def _meter_provider(settings: TelemetrySettings, resource: Resource) -> MeterProvider | None:
    if not settings.metrics_enabled:
        return None
    exporter = OTLPMetricExporter(endpoint=settings.metrics_endpoint)
    return MeterProvider(resource=resource, metric_readers=[PeriodicExportingMetricReader(exporter)])


def _tracer_provider(settings: TelemetrySettings, resource: Resource) -> TracerProvider:
    """``ALWAYS_ON``: o processo envia todo trace. Quem decide o que fica guardado é o destino,
    depois que o trace termina, porque só então se sabe se ele teve erro."""
    provider = TracerProvider(resource=resource, sampler=ALWAYS_ON)
    if settings.traces_enabled:
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.traces_endpoint))
        )
    return provider

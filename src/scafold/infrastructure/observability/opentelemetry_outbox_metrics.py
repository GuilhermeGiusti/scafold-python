"""Métricas da outbox com OpenTelemetry.

**Os gauges são observáveis e servem o snapshot do último ciclo.** O coletor lê mais vezes do que a
drenagem roda; um ``COUNT(*)`` por leitura seria carga no banco proporcional às leituras, e não ao
trabalho.

**A duração é gauge, não histograma**: o ciclo roda poucas vezes por minuto.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from opentelemetry.metrics import CallbackOptions, Counter, MeterProvider, Observation

from scafold.applications.ports.outbox_metrics import DeathReason, DispatchResult

#: O escopo de instrumentação, o mesmo do span de envio.
INSTRUMENTATION_SCOPE = "scafold.outbox"


class OpenTelemetryOutboxMetrics:
    """Implementa ``IOutboxMetrics``. O ``MeterProvider`` entra por construtor, nunca o global."""

    def __init__(self, meter_provider: MeterProvider) -> None:
        self._backlog: dict[str, tuple[int, float]] = {}
        self._last_drain_seconds = 0.0
        meter = meter_provider.get_meter(INSTRUMENTATION_SCOPE)
        self._dispatched: Counter = meter.create_counter(
            "outbox.dispatched", unit="{message}", description="Tentativas de entrega ao broker"
        )
        self._dead: Counter = meter.create_counter(
            "outbox.dead.messages", unit="{message}", description="Mensagens que viraram DEAD"
        )
        self._written: Counter = meter.create_counter(
            "events.published", unit="{event}", description="Eventos entregues a outbox"
        )
        meter.create_observable_gauge(
            "outbox.pending.messages",
            callbacks=[self._observe_pending],
            description="Mensagens PENDING, por dispatcher",
        )
        meter.create_observable_gauge(
            "outbox.oldest.pending.age",
            unit="s",
            callbacks=[self._observe_oldest],
            description="Idade da mensagem pendente mais antiga, por dispatcher",
        )
        meter.create_observable_gauge(
            "outbox.drain.last.duration",
            unit="s",
            callbacks=[self._observe_drain_duration],
            description="Duracao da ultima execucao da drenagem",
        )

    def record_attempt(self, *, event: str, destination: str, result: DispatchResult) -> None:
        self._dispatched.add(1, {"event": event, "destination": destination, "result": result})

    def record_dead(self, *, event: str, destination: str, reason: DeathReason) -> None:
        self._dead.add(1, {"event": event, "destination": destination, "reason": reason})

    def record_backlog(self, backlog: Mapping[str, tuple[int, float]]) -> None:
        self._backlog = dict(backlog)

    def record_drain_duration(self, seconds: float) -> None:
        self._last_drain_seconds = seconds

    def record_event_written(self, *, event: str) -> None:
        # `kind="integration"` conta o evento entregue à outbox, antes do commit. A entrega real ao
        # broker é `outbox.dispatched`.
        self._written.add(1, {"kind": "integration", "event": event})

    def _observe_pending(self, options: CallbackOptions) -> Iterable[Observation]:
        return [
            Observation(count, {"dispatcher": dispatcher})
            for dispatcher, (count, _) in self._backlog.items()
        ]

    def _observe_oldest(self, options: CallbackOptions) -> Iterable[Observation]:
        return [
            Observation(age, {"dispatcher": dispatcher})
            for dispatcher, (_, age) in self._backlog.items()
        ]

    def _observe_drain_duration(self, options: CallbackOptions) -> Iterable[Observation]:
        return [Observation(self._last_drain_seconds)]

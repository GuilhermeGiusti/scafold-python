"""Contrato de métricas do mecanismo de eventos de domínio."""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable


@runtime_checkable
class IDomainEventMetrics(Protocol):
    """Porta de métricas consumida por ``DomainEventDispatcher`` e ``DomainEventManager``.

    Fica em ``infrastructure/events/`` porque só esses dois a consomem: o domínio não fala de
    métrica. Os rótulos são de baixa cardinalidade (nome do evento, classe do handler, status);
    id de agregado e conteúdo do evento ficam no log. Adaptadores:
    ``OpenTelemetryDomainEventMetrics`` e ``LoggingDomainEventMetrics``.
    """

    def published(self, *, event_name: str) -> None:
        """Um evento foi enviado aos handlers. Métrica ``domain_events_published_total``."""
        ...

    def handled(
        self,
        *,
        event_name: str,
        handler: str,
        status: Literal["ok", "error"],
        duration_seconds: float,
    ) -> None:
        """Um handler terminou de tratar um evento.

        Métricas ``domain_event_handlers_total`` (por status) e
        ``domain_event_handler_duration_seconds`` (histograma).
        """
        ...

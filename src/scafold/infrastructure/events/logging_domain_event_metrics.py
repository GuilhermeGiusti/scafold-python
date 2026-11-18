"""Métricas de eventos de domínio escritas no log."""

from __future__ import annotations

import logging
from typing import Literal


class LoggingDomainEventMetrics:
    """Implementa ``IDomainEventMetrics`` escrevendo cada medição no log, em DEBUG.

    Serve para rodar sem coletor, ou com as métricas desligadas. Os nomes e rótulos são os da
    porta, no formato que o Prometheus exporia: trocar pelo adaptador OpenTelemetry não muda
    dispatcher, manager nem handlers. DEBUG porque é registro de rotina (``LOG_DEBUG=true``).
    """

    def __init__(self, logger: logging.Logger) -> None:
        self._log = logger

    def published(self, *, event_name: str) -> None:
        self._log.debug("domain_events_published_total{event_name=%s} +1", event_name)

    def handled(
        self,
        *,
        event_name: str,
        handler: str,
        status: Literal["ok", "error"],
        duration_seconds: float,
    ) -> None:
        self._log.debug(
            "domain_event_handlers_total{event_name=%s,handler=%s,status=%s} +1",
            event_name,
            handler,
            status,
        )
        self._log.debug(
            "domain_event_handler_duration_seconds{event_name=%s,handler=%s} %.6f",
            event_name,
            handler,
            duration_seconds,
        )

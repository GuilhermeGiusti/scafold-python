"""Métricas da outbox escritas no log."""

from __future__ import annotations

import logging
from collections.abc import Mapping

from scafold.applications.ports.outbox_metrics import DeathReason, DispatchResult


class LoggingOutboxMetrics:
    """Implementa ``IOutboxMetrics`` escrevendo cada medição no log, em DEBUG."""

    def __init__(self, logger: logging.Logger) -> None:
        self._log = logger

    def record_attempt(self, *, event: str, destination: str, result: DispatchResult) -> None:
        self._log.debug(
            "outbox_dispatched_total{event=%s,destination=%s,result=%s} +1",
            event,
            destination,
            result,
        )

    def record_dead(self, *, event: str, destination: str, reason: DeathReason) -> None:
        self._log.debug(
            "outbox_dead_messages_total{event=%s,destination=%s,reason=%s} +1",
            event,
            destination,
            reason,
        )

    def record_backlog(self, backlog: Mapping[str, tuple[int, float]]) -> None:
        for dispatcher, (pending, oldest) in backlog.items():
            self._log.debug("outbox_pending_messages{dispatcher=%s} %d", dispatcher, pending)
            self._log.debug(
                "outbox_oldest_pending_age_seconds{dispatcher=%s} %.3f", dispatcher, oldest
            )

    def record_drain_duration(self, seconds: float) -> None:
        self._log.debug("outbox_drain_last_duration_seconds %.6f", seconds)

    def record_event_written(self, *, event: str) -> None:
        self._log.debug("events_published_total{kind=integration,event=%s} +1", event)

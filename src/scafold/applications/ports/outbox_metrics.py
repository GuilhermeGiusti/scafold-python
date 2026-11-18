"""Porta das medições da outbox.

A drenagem e o gravador medem por aqui, sem conhecer a biblioteca de telemetria. Há dois
adaptadores em ``infrastructure/observability/``: o OpenTelemetry, com as métricas ligadas, e o
de log, com elas desligadas.

Nenhum id vira rótulo: ``event`` é o tipo do evento e ``destination`` é o destino lógico. Id de
mensagem e ``correlation_id`` ficam só nos spans (ADR-012).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal, Protocol

#: O resultado de uma tentativa de entrega, rótulo `result` de `outbox.dispatched`.
type DispatchResult = Literal["published", "transient_error", "permanent_error"]

RESULT_PUBLISHED: DispatchResult = "published"
RESULT_TRANSIENT: DispatchResult = "transient_error"
RESULT_PERMANENT: DispatchResult = "permanent_error"

#: Por que a mensagem morreu, rótulo `reason` de `outbox.dead.messages`.
type DeathReason = Literal["permanent", "attempts_exhausted"]

REASON_PERMANENT: DeathReason = "permanent"
REASON_ATTEMPTS_EXHAUSTED: DeathReason = "attempts_exhausted"


class IOutboxMetrics(Protocol):
    def record_attempt(self, *, event: str, destination: str, result: DispatchResult) -> None:
        """Uma tentativa de entrega (`outbox.dispatched`)."""
        ...

    def record_dead(self, *, event: str, destination: str, reason: DeathReason) -> None:
        """Uma mensagem que virou `DEAD` (`outbox.dead.messages`)."""
        ...

    def record_backlog(self, backlog: Mapping[str, tuple[int, float]]) -> None:
        """Por carimbo, as pendentes e a idade da mais antiga, em segundos, semeado com zero."""
        ...

    def record_drain_duration(self, seconds: float) -> None:
        """A duração do último ciclo (`outbox.drain.last.duration`)."""
        ...

    def record_event_written(self, *, event: str) -> None:
        """Um evento entregue ao gravador (`events.published`), antes do commit."""
        ...

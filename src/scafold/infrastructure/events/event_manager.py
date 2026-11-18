"""Registro dos handlers de eventos de domínio no sinal ``blinker``."""

from __future__ import annotations

import logging
from time import perf_counter
from typing import TYPE_CHECKING, Literal

from blinker import ANY, signal

if TYPE_CHECKING:
    from scafold.domain.shared.events.event_base import IDomainEvent, IDomainEventHandler
    from scafold.infrastructure.events.event_metrics import IDomainEventMetrics

DOMAIN_EVENTS_SIGNAL = "domain-events"
"""Nome do sinal ``blinker``. É global por nome no processo."""

log = logging.getLogger(__name__)


class DomainEventManager:
    """Registra handlers e os conecta ao sinal ``"domain-events"``.

    É aqui que a falha de um handler é tratada: cada ``handle`` roda isolado, a exceção vai para o
    log (``log.exception``) e para a métrica (``status="error"``), e o próximo handler roda mesmo
    assim. O dado já está comitado: nada é desfeito e nada chega ao use case.

    Três cuidados:

    - O sinal guarda só uma referência fraca ao receiver. Guarde o manager em algo que viva tanto
      quanto o processo (a ``Foundation`` da montagem), ou ele é coletado e os handlers param.
    - O sinal é global por nome: handlers registrados num teste vazam para o próximo se o manager
      não for limpo com ``clear``.
    - ``listener_to()`` é lido uma vez, no ``register``. Os handlers de um mesmo evento rodam na
      ordem de registro, e registrar duas vezes o mesmo handler não tem efeito.
    """

    def __init__(self, *, metrics: IDomainEventMetrics) -> None:
        self._signal = signal(DOMAIN_EVENTS_SIGNAL)
        self._metrics = metrics
        self._handlers: list[tuple[IDomainEventHandler, tuple[type[IDomainEvent], ...]]] = []

    def register(self, *handlers: IDomainEventHandler) -> None:
        for handler in handlers:
            if any(registered is handler for registered, _ in self._handlers):
                continue
            self._handlers.append((handler, tuple(handler.listener_to())))
        self._signal.connect(self._deliver)

    def clear(self) -> None:
        """Desconecta todos os receivers do sinal. Afeta todas as instâncias do processo."""
        for receiver in list(self._signal.receivers_for(ANY)):
            self._signal.disconnect(receiver)
        self._handlers.clear()

    def _deliver(self, sender: object, *, event: IDomainEvent) -> None:
        for handler, listened in self._handlers:
            if not isinstance(event, listened):
                continue
            name = type(handler).__name__
            started = perf_counter()
            status: Literal["ok", "error"] = "ok"
            try:
                handler.handle(event)
            except Exception:
                status = "error"
                log.exception("falha no handler %s ao tratar %s", name, event.name())
            self._metrics.handled(
                event_name=event.name(),
                handler=name,
                status=status,
                duration_seconds=perf_counter() - started,
            )

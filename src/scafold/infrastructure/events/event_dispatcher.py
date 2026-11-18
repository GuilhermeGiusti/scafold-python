"""Despacho de eventos de domínio pelo sinal ``blinker``."""

from __future__ import annotations

from collections.abc import Iterable

from blinker import signal

from scafold.domain.shared.aggregates.aggregate_root import AggregateRoot
from scafold.domain.shared.events.event_base import IDomainEvent
from scafold.infrastructure.events.event_manager import DOMAIN_EVENTS_SIGNAL
from scafold.infrastructure.events.event_metrics import IDomainEventMetrics


class DomainEventDispatcher:
    """Implementa ``IDomainEventDispatcher`` enviando pelo sinal ``"domain-events"``.

    É o adaptador que a montagem entrega aos use cases, que só conhecem a porta. O
    ``DomainEventManager`` fica do outro lado do sinal: registra os handlers e os conecta como
    receiver. Como o sinal é global por nome, qualquer dispatcher alcança qualquer manager do
    processo.
    """

    def __init__(self, *, metrics: IDomainEventMetrics) -> None:
        self._signal = signal(DOMAIN_EVENTS_SIGNAL)
        self._metrics = metrics

    def collect[IdT](self, aggregate: AggregateRoot[IdT]) -> set[IDomainEvent]:
        """Copia os eventos não comitados e limpa o agregado. Chame dentro da Unit of Work.

        A cópia é obrigatória: ``get_uncommitted_events`` devolve a referência interna, e
        ``clear_events`` a esvaziaria.
        """
        events = set(aggregate.get_uncommitted_events())
        aggregate.clear_events()
        return events

    def dispatch(self, events: Iterable[IDomainEvent]) -> None:
        """Envia cada evento pelo sinal e conta a publicação. Chame depois do commit."""
        for event in events:
            self._signal.send(self, event=event)
            self._metrics.published(event_name=event.name())

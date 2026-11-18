"""Handler que escuta todos os eventos de domínio."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from scafold.domain.shared.events.event_base import IDomainEvent


class AllEventsHandler:
    """Escuta ``IDomainEvent``, isto é, tudo.

    Como ``IDomainEvent`` é ``runtime_checkable`` e o manager filtra com ``isinstance``, qualquer
    evento de qualquer bounded context chega aqui. É o formato típico de auditoria: o handler não
    interpreta o evento, entrega ``to_json()`` a uma saída recebida de fora (``record``).
    """

    def __init__(self, record: Callable[[dict[str, Any]], None]) -> None:
        self._record = record

    def listener_to(self) -> list[type[IDomainEvent]]:
        return [IDomainEvent]

    def handle(self, event: IDomainEvent) -> None:
        self._record(event.to_json())

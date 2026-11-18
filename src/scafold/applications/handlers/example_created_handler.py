"""Handler de ``ExampleCreated``."""

from __future__ import annotations

from collections.abc import Callable

from scafold.domain.bounded_context_example.events.example_created import ExampleCreated
from scafold.domain.shared.events.event_base import IDomainEvent


class ExampleCreatedHandler:
    """Implementa ``IDomainEventHandler`` por estrutura, sem herança. Roda depois do commit.

    A ação de saída (``notify``) chega pelo construtor como função: o handler traduz o evento em
    mensagem e não conhece o canal. Não há ``try/except``: a falha sobe para o
    ``DomainEventManager``, que a registra no log e na métrica e segue para o próximo handler.
    O handler usa os campos do evento e não reabre o agregado.
    """

    def __init__(self, notify: Callable[[str], None]) -> None:
        self._notify = notify

    def listener_to(self) -> list[type[IDomainEvent]]:
        return [ExampleCreated]

    def handle(self, event: IDomainEvent) -> None:
        # O `isinstance` também estreita o tipo para o mypy.
        if not isinstance(event, ExampleCreated):
            return
        self._notify(f"example {event.aggregate_id} criado na categoria {event.category.value}")

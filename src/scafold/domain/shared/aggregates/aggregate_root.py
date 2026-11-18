"""Raiz de agregado: entidade que acumula os eventos de domínio de uma operação."""

from __future__ import annotations

from typing import Protocol

from scafold.domain.shared.entities.entity import Entity
from scafold.domain.shared.events.event_base import IDomainEvent


class AggregateRoot[IdT](Entity[IdT], Protocol):
    """Contrato com implementação padrão para a raiz de um agregado.

    A raiz é uma ``Entity`` (herda ``get_id``) e, além disso, registra os fatos que aconteceram
    com o agregado nesta operação. O agregado estende esta classe (herança explícita), implementa
    ``get_id`` e ganha ``add_event``, ``get_uncommitted_events`` e ``clear_events``.

    O conjunto ``events`` é criado de forma preguiçosa: um agregado ``@dataclass`` não precisa
    declará-lo, e um agregado reconstruído pelo repositório nasce sem eventos, porque eventos
    representam o que aconteceu nesta operação, não o histórico.

    Dentro do agregado, só ``add_event`` é usado, e sempre depois de validar a regra e mudar o
    estado: registrar antes faria sair um evento para uma mudança que não aconteceu.
    """

    events: set[IDomainEvent]

    def add_event(self, event: IDomainEvent) -> None:
        """Adiciona ``event`` ao conjunto ``events``, criando-o se não existir.

        O evento precisa ser hashable: use ``@dataclass(eq=False)`` na classe do evento, senão
        ``set.add`` levanta ``TypeError``.
        """
        if not hasattr(self, "events"):
            self.events = set()
        self.events.add(event)

    def get_uncommitted_events(self) -> set[IDomainEvent]:
        """Devolve o conjunto ``events``: a mesma referência, não uma cópia.

        Copie antes de chamar ``clear_events``: ``events = set(agg.get_uncommitted_events())``.
        """
        if not hasattr(self, "events"):
            return set()
        return self.events

    def clear_events(self) -> None:
        """Esvazia ``events``. Seguro em agregado que ainda não tem o atributo."""
        if hasattr(self, "events"):
            self.events.clear()

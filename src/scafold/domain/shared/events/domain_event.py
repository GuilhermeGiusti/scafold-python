"""Base concreta dos eventos de domínio."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from scafold.domain.shared.events.event_base import IDomainEvent


def _now_epoch() -> float:
    """Instante atual em epoch UTC."""
    return datetime.now(UTC).timestamp()


@dataclass(eq=False, kw_only=True)
class DomainEvent(IDomainEvent):
    """Implementa ``IDomainEvent`` e concentra o que todo evento tem em comum.

    Todo evento de domínio estende esta classe e implementa ``versioning``, ``name`` e
    ``to_json``; o mypy recusa uma subclasse que esqueça algum deles. A base fornece
    ``occurred_on`` (epoch UTC no instante da criação), keyword-only para não atrapalhar a ordem
    dos campos das subclasses.

    ``eq=False`` é obrigatório aqui e nas subclasses: o evento vive num ``set`` e precisa ser
    hashable. Com igualdade por identidade, dois eventos com os mesmos campos continuam sendo dois
    fatos distintos.
    """

    occurred_on: float = field(default_factory=_now_epoch)

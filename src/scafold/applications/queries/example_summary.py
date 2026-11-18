"""O resumo de um Example que a listagem devolve, sem reconstruir o agregado."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class ExampleSummary:
    """DTO do leitor dedicado. Mora em ``queries/``, ao lado da query, e não junto da porta do
    leitor (ADR-008): a porta o importa daqui."""

    id: UUID
    label: str
    item_count: int
    archived: bool

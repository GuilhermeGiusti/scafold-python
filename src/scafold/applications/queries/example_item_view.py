"""O que a leitura de um Example devolve para cada item."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from scafold.domain.bounded_context_example.entities.example_item import ExampleItem


@dataclass(frozen=True, slots=True, kw_only=True)
class ExampleItemView:
    id: UUID
    name: str
    position: int

    @classmethod
    def from_entity(cls, item: ExampleItem) -> ExampleItemView:
        return cls(id=item.id, name=item.name, position=item.position)

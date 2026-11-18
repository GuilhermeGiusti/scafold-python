"""Evento: item adicionado ao Example."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from scafold.domain.bounded_context_example.value_objects.example_id import ExampleId
from scafold.domain.bounded_context_example.value_objects.example_item_id import ExampleItemId
from scafold.domain.shared.events.domain_event import DomainEvent


@dataclass(eq=False)
class ExampleItemAdded(DomainEvent):
    """Um item entrou no Example. Carrega o id do item para os handlers."""

    aggregate_id: ExampleId
    item_id: ExampleItemId
    item_name: str

    def versioning(self) -> str:
        return "1"

    def name(self) -> str:
        return "bounded_context_example.example.item_added"

    def to_json(self) -> dict[str, Any]:
        return {
            "versioning": self.versioning(),
            "name": self.name(),
            "aggregate_id": str(self.aggregate_id),
            "item_id": str(self.item_id),
            "item_name": self.item_name,
            "occurred_on": self.occurred_on,
        }

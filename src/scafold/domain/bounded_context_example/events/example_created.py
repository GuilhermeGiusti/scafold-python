"""Evento: Example criado."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from scafold.domain.bounded_context_example.value_objects.category import Category
from scafold.domain.bounded_context_example.value_objects.example_id import ExampleId
from scafold.domain.shared.events.domain_event import DomainEvent


@dataclass(eq=False)
class ExampleCreated(DomainEvent):
    """Example criado. Emitido pela própria fábrica ``create``.

    Carrega o que os handlers precisam, para que eles não reabram o agregado.
    """

    aggregate_id: ExampleId
    label: str
    category: Category

    def versioning(self) -> str:
        return "1"

    def name(self) -> str:
        return "bounded_context_example.example.created"

    def to_json(self) -> dict[str, Any]:
        return {
            "versioning": self.versioning(),
            "name": self.name(),
            "aggregate_id": str(self.aggregate_id),
            "label": self.label,
            "category": self.category.value,
            "occurred_on": self.occurred_on,
        }

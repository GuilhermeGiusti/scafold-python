"""Evento: Example arquivado."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from scafold.domain.bounded_context_example.value_objects.example_id import ExampleId
from scafold.domain.shared.events.domain_event import DomainEvent


@dataclass(eq=False)
class ExampleArchived(DomainEvent):
    """Example arquivado. Um evento sem dados além do id carrega só ``aggregate_id``."""

    aggregate_id: ExampleId

    def versioning(self) -> str:
        return "1"

    def name(self) -> str:
        return "bounded_context_example.example.archived"

    def to_json(self) -> dict[str, Any]:
        return {
            "versioning": self.versioning(),
            "name": self.name(),
            "aggregate_id": str(self.aggregate_id),
            "occurred_on": self.occurred_on,
        }

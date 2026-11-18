"""O que a leitura de um Example devolve."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from scafold.applications.queries.example_item_view import ExampleItemView
from scafold.domain.bounded_context_example.aggregates.example import Example
from scafold.domain.bounded_context_example.value_objects.category import Category


@dataclass(frozen=True, slots=True, kw_only=True)
class ExampleView:
    """DTO de saída. O agregado não sai do use case: quem chama recebe uma cópia sem
    comportamento e não consegue chamar ``archive()`` por fora do use case que protege essa
    transição. O mapeamento do agregado para o DTO fica aqui, sem classe mapper (ADR-009)."""

    id: UUID
    label: str
    category: Category
    created_at: datetime
    archived_at: datetime | None
    items: tuple[ExampleItemView, ...]

    @classmethod
    def from_aggregate(cls, example: Example) -> ExampleView:
        return cls(
            id=example.id,
            label=example.label,
            category=example.category,
            created_at=example.created_at,
            archived_at=example.archived_at,
            items=tuple(ExampleItemView.from_entity(item) for item in example.items),
        )

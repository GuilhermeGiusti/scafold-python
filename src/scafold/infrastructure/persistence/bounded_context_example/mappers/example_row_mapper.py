"""Mapper de persistência: agregado para row, e row para agregado (ADR-009)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import ClassVar

from scafold.domain.bounded_context_example.aggregates.example import Example
from scafold.domain.bounded_context_example.entities.example_item import ExampleItem
from scafold.domain.bounded_context_example.value_objects.category import Category
from scafold.domain.bounded_context_example.value_objects.example_id import ExampleId
from scafold.domain.bounded_context_example.value_objects.example_item_id import ExampleItemId
from scafold.infrastructure.persistence.bounded_context_example.sqlc import models


class ExampleRowMapper:
    """Traduz entre o agregado e as linhas geradas pelo sqlc, nas duas direções.

    O banco guarda a categoria como um código de uma letra. Esse código é detalhe de
    armazenamento: fica aqui, e o agregado segue falando ``Category``. Sem este mapper, ou o
    agregado ganharia a forma da tabela, ou o repositório espalharia a conversão pelos métodos.

    Só traduz: não valida regra, não faz I/O e não guarda estado. Mora no adaptador de
    persistência, e o domínio e a aplicação nunca o importam.
    """

    _CODE_BY_CATEGORY: ClassVar[dict[Category, str]] = {
        Category.STANDARD: "S",
        Category.PREMIUM: "P",
    }
    _CATEGORY_BY_CODE: ClassVar[dict[str, Category]] = {
        code: category for category, code in _CODE_BY_CATEGORY.items()
    }

    def to_row(self, example: Example) -> models.Example:
        return models.Example(
            id=example.id,
            label=example.label,
            category_code=self._CODE_BY_CATEGORY[example.category],
            created_at=example.created_at,
            archived_at=example.archived_at,
        )

    def to_item_rows(self, example: Example) -> list[models.ExampleItem]:
        return [
            models.ExampleItem(
                id=item.id, example_id=example.id, name=item.name, position=item.position
            )
            for item in example.items
        ]

    def to_aggregate(self, row: models.Example, items: Sequence[models.ExampleItem]) -> Example:
        # Reconstrói pelo construtor, e não por `Example.create`: o que já foi gravado não é
        # validado de novo, não ganha id novo e nasce sem eventos.
        return Example(
            id=ExampleId(row.id),
            label=row.label,
            category=self._CATEGORY_BY_CODE[row.category_code],
            created_at=row.created_at,
            archived_at=row.archived_at,
            items=[
                ExampleItem(id=ExampleItemId(item.id), name=item.name, position=item.position)
                for item in items
            ],
        )

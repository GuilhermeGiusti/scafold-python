"""Entidade filha do agregado Example."""

from __future__ import annotations

from dataclasses import dataclass

from scafold.domain.bounded_context_example.value_objects.example_item_id import ExampleItemId
from scafold.domain.shared.entities.entity import Entity


@dataclass(eq=False)
class ExampleItem(Entity[ExampleItemId]):
    """Item de ``Example``.

    Tem identidade própria, mas só existe dentro do agregado: é criado por ``Example.add_item``,
    que garante o nome único entre os itens, e nunca é alterado por fora da raiz. Não estende
    ``AggregateRoot`` e não registra eventos: quem registra é a raiz.
    """

    id: ExampleItemId
    name: str
    position: int

    def get_id(self) -> ExampleItemId:
        return self.id

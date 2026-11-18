"""Agregado Example: a raiz que guarda as regras e é o único jeito de mudar seus itens."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from scafold.domain.bounded_context_example.entities.example_item import ExampleItem
from scafold.domain.bounded_context_example.errors.duplicate_item import DuplicateItem
from scafold.domain.bounded_context_example.errors.invalid_label import InvalidLabel
from scafold.domain.bounded_context_example.errors.invalid_transition import InvalidTransition
from scafold.domain.bounded_context_example.events.example_archived import ExampleArchived
from scafold.domain.bounded_context_example.events.example_created import ExampleCreated
from scafold.domain.bounded_context_example.events.example_item_added import ExampleItemAdded
from scafold.domain.bounded_context_example.value_objects.category import Category
from scafold.domain.bounded_context_example.value_objects.example_id import ExampleId
from scafold.domain.bounded_context_example.value_objects.example_item_id import ExampleItemId
from scafold.domain.shared.aggregates.aggregate_root import AggregateRoot

#: O tamanho máximo do nome. É o mesmo `varchar(64)` da migration e o `max_length` da API.
MAX_LABEL_LENGTH = 64


@dataclass(eq=False)
class Example(AggregateRoot[ExampleId]):
    """Raiz do agregado Example.

    Toda operação segue a mesma ordem: validar a regra, mudar o estado e só então registrar o
    evento. A regra quebrada vira um erro de domínio, e nada muda.

    ``eq=False`` mantém a igualdade por identidade e o hash padrão; sem isso o dataclass geraria
    igualdade por valor e tornaria o agregado unhashable.

    O instante e a categoria chegam de fora: o relógio é injetado no use case, e a categoria vem
    do serviço externo, pela porta ``ICategoryGateway``. O agregado não consulta nada sozinho.
    """

    id: ExampleId
    label: str
    category: Category
    created_at: datetime
    archived_at: datetime | None = None
    items: list[ExampleItem] = field(default_factory=list)

    @classmethod
    def create(cls, *, label: str, category: Category, now: datetime) -> Example:
        """Cria o agregado e registra ``ExampleCreated``.

        O nome perde os espaços das pontas e precisa ter de 1 a ``MAX_LABEL_LENGTH`` caracteres.
        Nome reprovado levanta ``InvalidLabel`` antes de qualquer criação.
        """
        normalized = label.strip()
        if not 1 <= len(normalized) <= MAX_LABEL_LENGTH:
            raise InvalidLabel("o nome precisa ter de 1 a 64 caracteres, sem os espacos das pontas")
        example = cls(id=ExampleId(uuid4()), label=normalized, category=category, created_at=now)
        example.add_event(
            ExampleCreated(aggregate_id=example.id, label=normalized, category=category)
        )
        return example

    def get_id(self) -> ExampleId:
        return self.id

    @property
    def is_archived(self) -> bool:
        return self.archived_at is not None

    def add_item(self, name: str) -> ExampleItem:
        """Cria um item dentro do agregado e registra ``ExampleItemAdded``.

        Invariantes, validadas antes de qualquer mudança: Example arquivado não recebe itens
        (``InvalidTransition``) e o nome é único entre os itens (``DuplicateItem``).
        """
        if self.is_archived:
            raise InvalidTransition("example arquivado nao aceita itens")
        if any(item.name == name for item in self.items):
            raise DuplicateItem("ja existe um item com esse nome no example")
        item = ExampleItem(id=ExampleItemId(uuid4()), name=name, position=len(self.items))
        self.items.append(item)
        self.add_event(ExampleItemAdded(aggregate_id=self.id, item_id=item.id, item_name=name))
        return item

    def archive(self, *, now: datetime) -> None:
        """Arquiva uma única vez e registra ``ExampleArchived``."""
        if self.is_archived:
            raise InvalidTransition("example ja arquivado")
        self.archived_at = now
        self.add_event(ExampleArchived(aggregate_id=self.id))

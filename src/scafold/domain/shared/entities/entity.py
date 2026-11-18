"""Entidade: objeto de domínio com identidade própria."""

from __future__ import annotations

from typing import Protocol


class Entity[IdT](Protocol):
    """Contrato de entidade: algo identificado por um ``IdT`` estável.

    Uma entidade que não é raiz vive dentro de um agregado e só é criada, alterada ou removida
    através da raiz, que protege as invariantes. A raiz também é uma entidade: ``AggregateRoot``
    estende este contrato e acrescenta o registro de eventos.

    Uso típico::

        @dataclass(eq=False)
        class ExampleItem(Entity[ExampleItemId]):
            id: ExampleItemId
            name: str

            def get_id(self) -> ExampleItemId:
                return self.id
    """

    def get_id(self) -> IdT:
        """Identificador da entidade. Cada entidade decide de onde ele vem."""
        ...

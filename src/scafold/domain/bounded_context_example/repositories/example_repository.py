"""Porta do repositório do agregado Example."""

from __future__ import annotations

from typing import Protocol

from scafold.domain.bounded_context_example.aggregates.example import Example
from scafold.domain.bounded_context_example.value_objects.example_id import ExampleId


class IExampleRepository(Protocol):
    """O que os use cases precisam para gravar e carregar um Example.

    Fala só de agregado, id e erro de domínio: nem transação nem SQL. As escritas acontecem dentro
    da transação que o use case abriu pela Unit of Work; o repositório nunca abre, commita nem
    reverte. A implementação SQL fica em ``infrastructure/persistence/bounded_context_example/``,
    e o fake em memória, em ``tests/support/``. Os dois passam pelo mesmo teste de contrato.
    """

    async def add(self, example: Example) -> None:
        """Grava o Example e seus itens. Levanta ``LabelTaken`` se o nome já existe."""
        ...

    async def get(self, example_id: ExampleId) -> Example | None:
        """Carrega o Example com os itens, ou ``None`` se ele não existe."""
        ...

    async def save(self, example: Example) -> None:
        """Grava o estado da raiz de um Example que já existe. Os itens só nascem na criação."""
        ...

    async def remove_archived(self) -> int:
        """Remove os Examples arquivados, com os itens, e devolve quantos saíram."""
        ...

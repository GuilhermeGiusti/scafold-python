"""Porta do leitor dedicado de Example: a leitura que não passa pelo agregado."""

from __future__ import annotations

from typing import Protocol

from scafold.applications.queries.example_summary import ExampleSummary


class IExampleReader(Protocol):
    """Leituras que devolvem DTO pronto, sem reconstruir o agregado.

    Uma leitura que precisa do agregado inteiro usa o repositório; uma que só mostra dados usa o
    leitor. O trabalho que o agregado faria em memória (contar itens) fica na query SQL.
    """

    async def list_summaries(self, *, limit: int) -> list[ExampleSummary]:
        """Os Examples, por nome, com a quantidade de itens. No máximo ``limit``."""
        ...

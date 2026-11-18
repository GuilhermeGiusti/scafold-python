"""Porta do serviço externo que classifica o nome de um Example."""

from __future__ import annotations

from typing import Protocol

from scafold.domain.bounded_context_example.value_objects.category import Category


class ICategoryGateway(Protocol):
    """Fala no vocabulário do domínio: recebe o nome e devolve uma ``Category``.

    O vocabulário do fornecedor (``tier``, ``GOLD``) nunca cruza esta porta. Quem traduz é o
    ``CategoryPayloadMapper``, dentro do adaptador em ``infrastructure/external/``.
    """

    async def classify(self, label: str) -> Category: ...

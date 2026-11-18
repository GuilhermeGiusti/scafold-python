"""Mapper anti-corrupção: payload do fornecedor para tipo do domínio, e o caminho inverso."""

from __future__ import annotations

from typing import ClassVar

from scafold.domain.bounded_context_example.value_objects.category import Category
from scafold.infrastructure.external.errors.unmapped_payload import UnmappedPayload
from scafold.infrastructure.external.fake_category_api import (
    ClassifyRequestPayload,
    ClassifyResponsePayload,
)


class CategoryPayloadMapper:
    """O vocabulário do fornecedor (``tier``, ``GOLD``, ``BASIC``) morre aqui.

    Sem este mapper, o use case leria ``payload["tier"]`` e o domínio passaria a falar a língua de um
    terceiro: trocar de fornecedor viraria mudança de regra de negócio. Com ele, a troca altera este
    arquivo e o cliente da API.
    """

    _CATEGORY_BY_TIER: ClassVar[dict[str, Category]] = {
        "GOLD": Category.PREMIUM,
        "BASIC": Category.STANDARD,
    }

    def to_request_payload(self, label: str) -> ClassifyRequestPayload:
        return {"text": label}

    def to_category(self, payload: ClassifyResponsePayload) -> Category:
        tier = payload["tier"]
        if tier not in self._CATEGORY_BY_TIER:
            # Termo novo do fornecedor não vira categoria por palpite: falha aqui, na fronteira.
            raise UnmappedPayload("tier desconhecido do fornecedor")
        return self._CATEGORY_BY_TIER[tier]

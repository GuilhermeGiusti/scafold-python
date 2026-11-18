"""A categoria de um Example, no vocabulário do domínio."""

from __future__ import annotations

from enum import StrEnum


class Category(StrEnum):
    """O domínio fala ``Category``, e só ele.

    Três vocabulários cercam este valor, e nenhum entra aqui: o banco grava um código de uma letra
    (``ExampleRowMapper``), o fornecedor externo fala ``tier`` (``CategoryPayloadMapper``) e a API
    devolve o texto do contrato HTTP (``ExamplePresenter``). Cada tradução mora no seu mapper.
    """

    STANDARD = "standard"
    PREMIUM = "premium"

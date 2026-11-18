"""Schemas HTTP de Example: o contrato da API, com os nomes que o cliente vê (ADR-011).

Todo campo de entrada tem tipo, restrição, exemplo e docstring; todo campo de saída tem tipo,
exemplo e docstring. A docstring vira a descrição do campo no Swagger.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, StrictStr

from scafold.infrastructure.rest.shared.schemas import RequestSchema, ResponseSchema

#: Um nome de item: texto estrito, de 1 a 64 caracteres. Alias simples, e não `type`, para o
#: Pydantic escrever a restrição no próprio campo do OpenAPI.
ItemName = Annotated[StrictStr, Field(min_length=1, max_length=64)]

#: O texto de uma categoria no contrato HTTP.
CategoryText = Literal["standard", "premium"]


class CreateExampleRequest(RequestSchema):
    """O que o cliente envia para criar um Example."""

    # `StrictStr`: número não é convertido em texto. `3` não vira `"3"`.
    display_name: Annotated[
        StrictStr,
        Field(alias="displayName", min_length=1, max_length=64, examples=["Relatório premium"]),
    ]
    """Nome exibido do Example. É único: dois Examples não têm o mesmo nome. Um nome que contém
    "premium" é classificado na categoria premium."""

    item_names: Annotated[
        list[ItemName], Field(alias="itemNames", max_length=20, examples=[["Capa", "Sumário"]])
    ] = []
    """Os nomes dos itens, na ordem. Até 20, sem repetir nome."""


class ExampleCreatedResponse(ResponseSchema):
    """O Example que acabou de ser criado."""

    id: Annotated[UUID, Field(examples=["0b6f3c52-9d0f-4d0e-8a43-5b8f6f1a2c11"])]
    """Identificador gerado na criação."""


class ExampleItemResponse(ResponseSchema):
    """Um item de um Example."""

    id: Annotated[UUID, Field(examples=["7f0c1c1e-3a5b-4c57-9d0e-2a1b3c4d5e6f"])]
    """Identificador do item."""

    name: Annotated[str, Field(examples=["Capa"])]
    """Nome do item, único dentro do Example."""

    position: Annotated[int, Field(examples=[0])]
    """Posição do item na lista, a partir de 0."""


class ExampleResponse(ResponseSchema):
    """Um Example inteiro, como o cliente o vê."""

    id: Annotated[UUID, Field(examples=["0b6f3c52-9d0f-4d0e-8a43-5b8f6f1a2c11"])]
    """Identificador gerado na criação."""

    display_name: Annotated[
        str, Field(serialization_alias="displayName", examples=["Relatório premium"])
    ]
    """Nome exibido do Example."""

    category: Annotated[CategoryText, Field(examples=["premium"])]
    """Categoria atribuída pelo serviço de classificação na criação."""

    created_at: Annotated[
        datetime, Field(serialization_alias="createdAt", examples=["2026-11-18T12:00:00Z"])
    ]
    """Instante em que o Example foi criado."""

    archived_at: Annotated[
        datetime | None,
        Field(serialization_alias="archivedAt", examples=["2026-11-19T08:30:00Z"]),
    ]
    """Instante em que o Example foi arquivado, ou nulo enquanto ele está ativo."""

    items: Annotated[list[ExampleItemResponse], Field(examples=[[]])]
    """Os itens do Example, na ordem."""


class ExampleSummaryResponse(ResponseSchema):
    """O resumo de um Example na listagem."""

    id: Annotated[UUID, Field(examples=["0b6f3c52-9d0f-4d0e-8a43-5b8f6f1a2c11"])]
    """Identificador do Example."""

    display_name: Annotated[
        str, Field(serialization_alias="displayName", examples=["Relatório premium"])
    ]
    """Nome exibido do Example."""

    item_count: Annotated[int, Field(serialization_alias="itemCount", examples=[2])]
    """Quantidade de itens do Example."""

    archived: Annotated[bool, Field(examples=[False])]
    """Verdadeiro quando o Example foi arquivado."""


class ExampleListResponse(ResponseSchema):
    """Uma página de Examples, por nome."""

    items: Annotated[list[ExampleSummaryResponse], Field(examples=[[]])]
    """Os Examples encontrados, no máximo `limit`."""

"""Os schemas que toda borda REST do módulo usa: as bases e o formato de erro.

Ficam aqui, e não no arquivo de um agregado, para que todos os agregados usem os mesmos.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class RequestSchema(BaseModel):
    """Base de todo schema de entrada: campo desconhecido é recusado, e a docstring de cada campo
    vira a descrição dele no Swagger."""

    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)


class ResponseSchema(BaseModel):
    """Base de todo schema de saída."""

    model_config = ConfigDict(use_attribute_docstrings=True)


class ErrorResponse(ResponseSchema):
    """O corpo de todo erro da API."""

    code: Annotated[str, Field(examples=["example_not_found"])]
    """Código estável do erro, para o cliente tratar por programa."""

    message: Annotated[str, Field(examples=["Example não encontrado."])]
    """Texto do erro, para leitura humana."""


class InvalidField(ResponseSchema):
    """Um campo da entrada que não passou na validação."""

    field: Annotated[str, Field(examples=["body.displayName"])]
    """Caminho do campo: onde ele veio (`body`, `query` ou `path`) e o nome dele.

    A regra que o campo descumpriu não vem aqui: ela está na documentação do campo.
    """


class ValidationErrorResponse(ErrorResponse):
    """O corpo do erro de validação da entrada: o erro comum, mais os campos recusados."""

    fields: Annotated[list[InvalidField], Field(examples=[[{"field": "body.displayName"}]])]
    """Os campos recusados, cada um uma vez."""

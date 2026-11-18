"""Use case de query: ler um Example inteiro."""

from __future__ import annotations

from scafold.applications.errors.example_not_found import ExampleNotFound
from scafold.applications.queries.example_view import ExampleView
from scafold.applications.queries.get_example_query import GetExampleQuery
from scafold.applications.shared.use_case import AsyncUseCase
from scafold.domain.bounded_context_example.repositories.example_repository import (
    IExampleRepository,
)
from scafold.domain.bounded_context_example.value_objects.example_id import ExampleId


class GetExampleUseCase(AsyncUseCase[GetExampleQuery, ExampleView]):
    """Query não abre transação: o repositório pede a conexão sozinho, e as queries saem com
    ``transaction="none"`` na métrica. Devolve DTO; o agregado não sai daqui."""

    def __init__(self, *, repository: IExampleRepository) -> None:
        self._repository = repository

    async def execute(self, input: GetExampleQuery) -> ExampleView:
        example = await self._repository.get(ExampleId(input.example_id))
        if example is None:
            raise ExampleNotFound("example nao encontrado")
        return ExampleView.from_aggregate(example)

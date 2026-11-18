"""Use case de query: listar Examples pelo leitor dedicado."""

from __future__ import annotations

from scafold.applications.ports.example_reader import IExampleReader
from scafold.applications.queries.example_summary import ExampleSummary
from scafold.applications.queries.list_examples_query import ListExamplesQuery
from scafold.applications.shared.use_case import AsyncUseCase


class ListExamplesUseCase(AsyncUseCase[ListExamplesQuery, list[ExampleSummary]]):
    """Uma listagem só mostra dados, então usa o leitor e não reconstrói agregados."""

    def __init__(self, *, reader: IExampleReader) -> None:
        self._reader = reader

    async def execute(self, input: ListExamplesQuery) -> list[ExampleSummary]:
        return await self._reader.list_summaries(limit=input.limit)

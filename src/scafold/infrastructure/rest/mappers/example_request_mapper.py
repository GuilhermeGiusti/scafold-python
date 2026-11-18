"""Mapper de entrada da borda REST: request schema para command ou query (ADR-009)."""

from __future__ import annotations

from uuid import UUID

from scafold.applications.commands.archive_example_command import ArchiveExampleCommand
from scafold.applications.commands.create_example_command import CreateExampleCommand
from scafold.applications.queries.get_example_query import GetExampleQuery
from scafold.applications.queries.list_examples_query import ListExamplesQuery
from scafold.infrastructure.rest.example_schemas import CreateExampleRequest


class ExampleRequestMapper:
    """Um método por pedido. É aqui que o nome do contrato HTTP vira o nome da aplicação: o campo
    ``displayName`` do request vira o ``label`` do command.

    Só traduz: um nome em branco passa por aqui sem erro, porque quem o recusa é o domínio.
    """

    def to_create_command(self, request: CreateExampleRequest) -> CreateExampleCommand:
        return CreateExampleCommand(label=request.display_name, item_names=tuple(request.item_names))

    def to_archive_command(self, example_id: UUID) -> ArchiveExampleCommand:
        return ArchiveExampleCommand(example_id=example_id)

    def to_get_query(self, example_id: UUID) -> GetExampleQuery:
        return GetExampleQuery(example_id=example_id)

    def to_list_query(self, limit: int) -> ListExamplesQuery:
        return ListExamplesQuery(limit=limit)

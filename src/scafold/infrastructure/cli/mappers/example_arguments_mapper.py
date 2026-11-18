"""Mapper de entrada da borda de linha de comando: argumentos para command ou query."""

from __future__ import annotations

from argparse import Namespace

from scafold.applications.commands.archive_example_command import ArchiveExampleCommand
from scafold.applications.commands.create_example_command import CreateExampleCommand
from scafold.applications.queries.get_example_query import GetExampleQuery
from scafold.applications.queries.list_examples_query import ListExamplesQuery


class ExampleArgumentsMapper:
    """Um método por comando. Os argumentos já chegam com tipo e restrição conferidos pelo
    ``argparse``; o mapper só traduz, e a regra de negócio fica com o domínio."""

    def to_create_command(self, arguments: Namespace) -> CreateExampleCommand:
        return CreateExampleCommand(label=arguments.label, item_names=tuple(arguments.items))

    def to_archive_command(self, arguments: Namespace) -> ArchiveExampleCommand:
        return ArchiveExampleCommand(example_id=arguments.example_id)

    def to_get_query(self, arguments: Namespace) -> GetExampleQuery:
        return GetExampleQuery(example_id=arguments.example_id)

    def to_list_query(self, arguments: Namespace) -> ListExamplesQuery:
        return ListExamplesQuery(limit=arguments.limit)

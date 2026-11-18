"""Borda de linha de comando de Example: argumentos para use case, e use case para JSON.

Como a borda REST, ela não tem regra: valida tipo e formato dos argumentos (``argparse``), traduz
pelo mapper, chama o use case já envolvido pelo decorator e devolve o texto do presenter.
"""

from __future__ import annotations

import argparse
from uuid import UUID

from scafold.applications.commands.archive_example_command import ArchiveExampleCommand
from scafold.applications.commands.create_example_command import CreateExampleCommand
from scafold.applications.queries.example_summary import ExampleSummary
from scafold.applications.queries.example_view import ExampleView
from scafold.applications.queries.get_example_query import GetExampleQuery
from scafold.applications.queries.list_examples_query import ListExamplesQuery
from scafold.applications.shared.use_case import (
    AsyncExecuterUseCase,
    AsyncUnitUseCase,
    AsyncUseCase,
)
from scafold.domain.bounded_context_example.value_objects.example_id import ExampleId
from scafold.infrastructure.cli.mappers.example_arguments_mapper import ExampleArgumentsMapper
from scafold.infrastructure.cli.presenters.example_cli_presenter import ExampleCliPresenter

#: O limite da listagem, o mesmo da API.
MAX_LIMIT = 100


def _limit(raw: str) -> int:
    """Tipo e restrição do ``--limit``, conferidos na borda."""
    try:
        value = int(raw)
    except ValueError:
        raise argparse.ArgumentTypeError("--limit aceita um inteiro de 1 a 100") from None
    if not 1 <= value <= MAX_LIMIT:
        raise argparse.ArgumentTypeError("--limit aceita um inteiro de 1 a 100")
    return value


class ExampleCli:
    def __init__(
        self,
        *,
        create: AsyncUseCase[CreateExampleCommand, ExampleId],
        archive: AsyncUnitUseCase[ArchiveExampleCommand],
        get: AsyncUseCase[GetExampleQuery, ExampleView],
        list_all: AsyncUseCase[ListExamplesQuery, list[ExampleSummary]],
        purge: AsyncExecuterUseCase,
        mapper: ExampleArgumentsMapper,
        presenter: ExampleCliPresenter,
    ) -> None:
        self._create = create
        self._archive = archive
        self._get = get
        self._list_all = list_all
        self._purge = purge
        self._mapper = mapper
        self._presenter = presenter

    @staticmethod
    def add_commands(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        """Declara os comandos. Não depende de use case: ``--help`` funciona sem configuração."""
        create = commands.add_parser("create-example", help="cria um Example")
        create.add_argument("--label", required=True, help="nome do Example, unico")
        create.add_argument(
            "--item", dest="items", action="append", default=[], help="nome de um item; repita"
        )

        archive = commands.add_parser("archive-example", help="arquiva um Example")
        archive.add_argument("--id", dest="example_id", type=UUID, required=True)

        get = commands.add_parser("get-example", help="mostra um Example com os itens")
        get.add_argument("--id", dest="example_id", type=UUID, required=True)

        listing = commands.add_parser("list-examples", help="lista os Examples por nome")
        listing.add_argument("--limit", type=_limit, default=20)

        commands.add_parser("purge-archived-examples", help="remove os Examples arquivados")

    def presents(self, error: Exception) -> bool:
        return isinstance(error, ExampleCliPresenter.PRESENTABLE)

    def present_error(self, error: Exception) -> str:
        return self._presenter.present_error(error)

    async def execute(self, arguments: argparse.Namespace) -> str:
        match arguments.command:
            case "create-example":
                example_id = await self._create.execute(self._mapper.to_create_command(arguments))
                return self._presenter.present_created(example_id)
            case "archive-example":
                await self._archive.execute(self._mapper.to_archive_command(arguments))
                return self._presenter.present_done()
            case "get-example":
                view = await self._get.execute(self._mapper.to_get_query(arguments))
                return self._presenter.present_view(view)
            case "list-examples":
                summaries = await self._list_all.execute(self._mapper.to_list_query(arguments))
                return self._presenter.present_list(summaries)
            case "purge-archived-examples":
                await self._purge.execute()
                return self._presenter.present_done()
            case unknown:
                raise ValueError(f"comando desconhecido: {unknown}")

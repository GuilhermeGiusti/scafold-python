"""A borda de linha de comando: o parser, a execução de um comando e os códigos de saída.

A ordem do boot é a mesma da API: argumentos, configuração, log, telemetria, fundação e o comando.
Argumento inválido sai pelo ``argparse`` antes de qualquer configuração, e ``--help`` funciona sem
ambiente. O comando roda dentro de ``asyncio.run``, que abre e fecha o pool no mesmo event loop.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from collections.abc import Mapping, Sequence
from typing import TextIO

from scafold.bootstrap.composition import LOGGER_NAME, UseCases, build_foundation
from scafold.bootstrap.settings import ConfigurationError, Settings
from scafold.bootstrap.telemetry import Telemetry, build_telemetry
from scafold.infrastructure.cli.example_cli import ExampleCli
from scafold.infrastructure.cli.mappers.example_arguments_mapper import ExampleArgumentsMapper
from scafold.infrastructure.cli.presenters.example_cli_presenter import ExampleCliPresenter
from scafold.infrastructure.observability.json_log_formatter import configure_logging

#: O comando terminou bem; a saída padrão tem o JSON do resultado.
EXIT_OK = 0
#: Configuração recusada ou defeito; o defeito vai para o log, em ERROR.
EXIT_FAILURE = 1
#: Argumento inválido, recusado pelo `argparse`.
EXIT_USAGE = 2
#: O pedido foi recusado por uma regra; a saída de erro tem o JSON com `code` e `message`.
EXIT_REFUSED = 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scafold", description="Executa um use case do scafold pela linha de comando."
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="comando")
    ExampleCli.add_commands(commands)
    return parser


def build_example_cli(use_cases: UseCases) -> ExampleCli:
    return ExampleCli(
        create=use_cases.create_example,
        archive=use_cases.archive_example,
        get=use_cases.get_example,
        list_all=use_cases.list_examples,
        purge=use_cases.purge_archived_examples,
        mapper=ExampleArgumentsMapper(),
        presenter=ExampleCliPresenter(),
    )


async def execute(
    cli: ExampleCli, arguments: argparse.Namespace, *, stdout: TextIO, stderr: TextIO
) -> int:
    """Roda um comando já validado. Recusa esperada vira JSON na saída de erro; defeito sobe."""
    try:
        output = await cli.execute(arguments)
    except Exception as error:
        if not cli.presents(error):
            raise
        print(cli.present_error(error), file=stderr)
        return EXIT_REFUSED
    print(output, file=stdout)
    return EXIT_OK


def run(
    argv: Sequence[str], environment: Mapping[str, str], *, stdout: TextIO, stderr: TextIO
) -> int:
    """Lê os argumentos e a configuração e executa o comando. Devolve o código de saída."""
    try:
        arguments = build_parser().parse_args(argv)
    except SystemExit as exit_request:
        return exit_request.code if isinstance(exit_request.code, int) else EXIT_USAGE

    try:
        settings = Settings.from_environment(environment)
    except ConfigurationError as refusal:
        # Uma linha, com o nome da variável e o formato esperado, nunca o valor recebido.
        print(str(refusal), file=stderr)
        return EXIT_FAILURE

    configure_logging(service=settings.service_name, level=settings.log_level)
    logger = logging.getLogger(LOGGER_NAME)
    telemetry = build_telemetry(settings)
    try:
        return asyncio.run(_run_with_foundation(arguments, settings, telemetry, stdout, stderr))
    except Exception:
        logger.exception("falha ao executar o comando")
        return EXIT_FAILURE
    finally:
        telemetry.shutdown()


async def _run_with_foundation(
    arguments: argparse.Namespace,
    settings: Settings,
    telemetry: Telemetry,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    foundation = build_foundation(settings=settings, telemetry=telemetry)
    try:
        cli = build_example_cli(foundation.use_cases)
        return await execute(cli, arguments, stdout=stdout, stderr=stderr)
    finally:
        await foundation.close()

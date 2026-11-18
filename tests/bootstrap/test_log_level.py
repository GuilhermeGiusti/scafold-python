import io
import json
import logging
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from scafold.bootstrap.settings import LOG_DEBUG_VARIABLE, log_level, switch
from scafold.infrastructure.observability.json_log_formatter import (
    ERROR_FIELDS,
    LOG_FIELDS,
    configure_logging,
)

scenarios("bootstrap/log_level.feature")

LEVELS = (logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR)


@pytest.fixture
def output() -> io.StringIO:
    return io.StringIO()


#: Os loggers que os cenários usam. Em DEBUG, outras bibliotecas do processo de teste também
#: escrevem, e o cenário só olha as linhas que ele mesmo escreveu.
SCENARIO_LOGGERS = frozenset({"scafold.test", "third_party.client"})


def entries(output: io.StringIO) -> list[dict[str, Any]]:
    lines = [json.loads(line) for line in output.getvalue().splitlines()]
    return [line for line in lines if line["logger"] in SCENARIO_LOGGERS]


@given(parsers.parse('o log configurado com LOG_DEBUG igual a "{value}"'))
def _(output: io.StringIO, value: str) -> None:
    debug = switch({LOG_DEBUG_VARIABLE: value}, LOG_DEBUG_VARIABLE, default=False)
    configure_logging(service="scafold-test", level=log_level(debug), stream=output)


@when("o processo registra uma linha em cada nível")
def _() -> None:
    logger = logging.getLogger("scafold.test")
    for level in LEVELS:
        logger.log(level, "linha em %s", logging.getLevelName(level))


@when("uma biblioteca de terceiros registra uma linha em cada nível")
def _() -> None:
    logger = logging.getLogger("third_party.client")
    for level in LEVELS:
        logger.log(level, "linha em %s", logging.getLevelName(level))


@when(parsers.parse('o processo registra uma exceção com a mensagem "{message}"'))
def _(message: str) -> None:
    try:
        raise RuntimeError(message)
    except RuntimeError:
        logging.getLogger("scafold.test").exception("falha ao atender")


@then(parsers.parse('aparecem no log exatamente os níveis "{levels}"'))
def _(output: io.StringIO, levels: str) -> None:
    assert [entry["level"] for entry in entries(output)] == levels.split(", ")


@then(
    parsers.parse(
        'a linha do erro tem os campos fixos, o tipo de erro "{error_type}" e a pilha'
    )
)
def _(output: io.StringIO, error_type: str) -> None:
    [entry] = entries(output)
    assert tuple(entry) == LOG_FIELDS + ERROR_FIELDS
    assert entry["error_type"] == error_type
    assert "test_log_level.py" in entry["stack"]


@then(parsers.parse('"{secret}" não aparece no log'))
def _(output: io.StringIO, secret: str) -> None:
    assert output.getvalue()
    assert secret not in output.getvalue()

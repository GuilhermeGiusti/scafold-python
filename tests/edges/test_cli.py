import io
import json
import shlex

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from scafold.bootstrap.cli import build_example_cli, build_parser, execute, run as run_process

from ..conftest import Run
from ..support.scene import Scene

scenarios("edges/cli.feature")


@pytest.fixture
def stdout() -> io.StringIO:
    return io.StringIO()


@pytest.fixture
def stderr() -> io.StringIO:
    return io.StringIO()


def over_fakes(
    run: Run, scene: Scene, command: str, stdout: io.StringIO, stderr: io.StringIO
) -> int:
    """O comando sobre os fakes: o mesmo parser e a mesma borda do processo."""
    arguments = build_parser().parse_args(shlex.split(command))
    code: int = run(
        execute(build_example_cli(scene.use_cases), arguments, stdout=stdout, stderr=stderr)
    )
    return code


@given(parsers.parse('o comando "{command}" executado'))
def _(run: Run, scene: Scene, command: str) -> None:
    assert over_fakes(run, scene, command, io.StringIO(), io.StringIO()) == 0


@when(parsers.parse('executo o comando "{command}"'), target_fixture="exit_code")
def _(run: Run, scene: Scene, stdout: io.StringIO, stderr: io.StringIO, command: str) -> int:
    return over_fakes(run, scene, command, stdout, stderr)


@when(
    parsers.parse('executo o processo com o comando "{command}" e sem configuração'),
    target_fixture="exit_code",
)
def _(stdout: io.StringIO, stderr: io.StringIO, command: str) -> int:
    return run_process(shlex.split(command), {}, stdout=stdout, stderr=stderr)


@then(parsers.parse("o comando termina com o código {code:d}"))
def _(exit_code: int, code: int) -> None:
    assert exit_code == code


@then(parsers.parse('a saída padrão tem o JSON com o campo "{field}"'))
def _(stdout: io.StringIO, field: str) -> None:
    assert field in json.loads(stdout.getvalue())


@then(parsers.parse('a saída padrão lista os nomes "{names}"'))
def _(stdout: io.StringIO, names: str) -> None:
    assert [item["label"] for item in json.loads(stdout.getvalue())] == names.split(", ")


@then(parsers.parse('a saída de erro tem o código "{code}"'))
def _(stderr: io.StringIO, code: str) -> None:
    assert json.loads(stderr.getvalue())["code"] == code


@then(parsers.parse('a saída de erro cita a variável "{name}"'))
def _(stderr: io.StringIO, name: str) -> None:
    assert name in stderr.getvalue()

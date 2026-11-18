from collections.abc import Callable
from pathlib import Path

from pytest_bdd import parsers, scenarios, then, when

from ..support.schema_rules import (
    forbidden_objects,
    instant_defaults,
    orm_imports,
    unnamed_constraints,
)

scenarios("architecture/schema_and_orm.feature")

PROJECT = Path(__file__).resolve().parents[2]

#: A frase do cenário para a regra que ela aplica.
SCHEMA_RULES: dict[str, Callable[[str], list[str]]] = {
    "objetos que fazem o banco agir": forbidden_objects,
    "DEFAULT de instante": instant_defaults,
    "restrições sem nome": unnamed_constraints,
}


@when("procuro imports do ORM no projeto", target_fixture="outcome")
def _() -> list[str]:
    files = sorted([*(PROJECT / "src").rglob("*.py"), *(PROJECT / "tests").rglob("*.py")])
    return [
        f"{path.relative_to(PROJECT)}: {found}"
        for path in files
        for found in orm_imports(path.read_text(encoding="utf-8"), str(path))
    ]


@when(parsers.parse('procuro imports do ORM no código "{source}"'), target_fixture="outcome")
def _(source: str) -> list[str]:
    return orm_imports(source.replace("\\n", "\n"))


@when(
    parsers.parse('aplico a regra "{rule}" às migrations do projeto'), target_fixture="outcome"
)
def _(rule: str) -> list[str]:
    return [
        f"{path.relative_to(PROJECT)}: {found}"
        for path in sorted((PROJECT / "migrations").rglob("*.sql"))
        for found in SCHEMA_RULES[rule](path.read_text(encoding="utf-8"))
    ]


@when(parsers.parse('aplico a regra "{rule}" ao SQL "{sql}"'), target_fixture="outcome")
def _(rule: str, sql: str) -> list[str]:
    return SCHEMA_RULES[rule](sql)


@then("nada é encontrado")
def _(outcome: list[str]) -> None:
    assert outcome == []


@then(parsers.parse('são encontrados "{found}"'))
def _(outcome: list[str], found: str) -> None:
    assert outcome == found.split(", ")


@then("a regra encontra uma violação")
def _(outcome: list[str]) -> None:
    assert len(outcome) == 1, outcome

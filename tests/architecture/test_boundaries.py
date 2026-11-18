import ast
from pathlib import Path

from pytest_bdd import parsers, scenarios, then, when

scenarios("architecture/boundaries.feature")

PROJECT = Path(__file__).resolve().parents[2]
PACKAGE = PROJECT / "src" / "scafold"


def imported_modules(source: str) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    return modules


def environment_reads(source: str) -> list[str]:
    """``os.environ`` e ``os.getenv``, lidos pela árvore sintática."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Attribute) and node.attr in {"environ", "getenv"}:
            if isinstance(node.value, ast.Name) and node.value.id == "os":
                found.append(f"os.{node.attr}")
        elif isinstance(node, ast.ImportFrom) and node.module == "os":
            found.extend(f"os.{alias.name}" for alias in node.names if alias.name in {"environ", "getenv"})
    return found


@when(parsers.parse('procuro os imports da camada "{layer}"'), target_fixture="outcome")
def _(layer: str) -> set[str]:
    modules: set[str] = set()
    for path in (PACKAGE / layer).rglob("*.py"):
        modules |= imported_modules(path.read_text(encoding="utf-8"))
    return modules


@when(parsers.parse('procuro os imports do código "{source}"'), target_fixture="outcome")
def _(source: str) -> set[str]:
    return imported_modules(source)


@when(parsers.parse('procuro quem lê o ambiente em "{folder}"'), target_fixture="outcome")
def _(folder: str) -> list[str]:
    return [
        f"{path.relative_to(PROJECT)}: {read}"
        for path in (PROJECT / folder).rglob("*.py")
        for read in environment_reads(path.read_text(encoding="utf-8"))
    ]


@when(parsers.parse('procuro quem lê o ambiente no código "{source}"'), target_fixture="outcome")
def _(source: str) -> list[str]:
    return environment_reads(source.replace("\\n", "\n"))


@then(parsers.parse('nenhum começa com "{forbidden}"'))
def _(outcome: set[str], forbidden: str) -> None:
    prefixes = tuple(prefix.strip() for prefix in forbidden.split(","))
    assert {module for module in outcome if module.startswith(prefixes)} == set()


@then(parsers.parse('"{module}" é encontrado'))
def _(outcome: set[str], module: str) -> None:
    assert module in outcome


@then("ninguém é encontrado")
def _(outcome: list[str]) -> None:
    assert outcome == []


@then("alguém é encontrado")
def _(outcome: list[str]) -> None:
    assert outcome

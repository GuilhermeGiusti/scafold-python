from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

from ..support.openapi_rules import RULES
from ..support.undocumented_app import build_undocumented_app

scenarios("rest/openapi_contract.feature")


@given("uma aplicação com rotas escritas sem documentação", target_fixture="app")
def _() -> FastAPI:
    return build_undocumented_app()


@when(parsers.parse("procuro {violation}"), target_fixture="violations")
def _(app: FastAPI, client: TestClient, violation: str) -> list[str]:
    # `app.openapi()` não depende da rota `/openapi.json`: a regra vale com o Swagger desligado.
    return RULES[violation](app.openapi(), client)


@then("nada é encontrado")
def _(violations: list[str]) -> None:
    assert violations == []


@then(parsers.parse('a rota "{route}" é encontrada'))
def _(violations: list[str], route: str) -> None:
    assert any(violation.startswith(f"{route}:") for violation in violations), violations


@then(parsers.parse('a rota "{route}" não é encontrada'))
def _(violations: list[str], route: str) -> None:
    assert not any(violation.startswith(f"{route}:") for violation in violations), violations

from typing import Any, cast

import schemathesis
from fastapi import FastAPI
from hypothesis import HealthCheck, given, settings
from pytest_bdd import parsers, scenarios, then, when
from schemathesis.core.result import Ok
from schemathesis.specs.openapi.checks import positive_data_acceptance

scenarios("rest/documented_behavior.feature")

MODES = {
    "válidas": schemathesis.GenerationMode.POSITIVE,
    "inválidas": schemathesis.GenerationMode.NEGATIVE,
}

EXCLUDED = cast(schemathesis.CheckFunction, positive_data_acceptance)

#: Requisições geradas por rota e por tipo.
EXAMPLES_PER_ROUTE = 40


def has_input(operation: schemathesis.APIOperation[Any, Any, Any, Any]) -> bool:
    """A rota declara parâmetro ou corpo? Sem entrada, não há requisição inválida a gerar."""
    raw: dict[str, Any] = operation.definition.raw
    return bool(raw.get("parameters")) or "requestBody" in raw


def exercise(
    operation: schemathesis.APIOperation[Any, Any, Any, Any], mode: schemathesis.GenerationMode
) -> None:
    @given(case=operation.as_strategy(generation_mode=mode))
    @settings(
        max_examples=EXAMPLES_PER_ROUTE, deadline=None, suppress_health_check=list(HealthCheck)
    )
    def check(case: schemathesis.Case[Any]) -> None:
        # Confere, entre outras coisas, que o status está documentado na rota e que o corpo
        # segue o schema daquele status. `positive_data_acceptance` fica de fora: para o JSON
        # Schema, `5.0` é um inteiro válido, e o modo estrito o recusa de propósito.
        case.validate_response(case.call(), excluded_checks=[EXCLUDED])

    check()


@when(
    parsers.parse(
        "exercito cada rota com requisições {kind} geradas a partir do documento OpenAPI"
    ),
    target_fixture="failures",
)
def _(app: FastAPI, kind: str) -> list[str]:
    schema = schemathesis.openapi.from_asgi("/openapi.json", app)
    failures = []
    for result in schema.get_all_operations():
        assert isinstance(result, Ok)
        operation = result.ok()
        if MODES[kind] is schemathesis.GenerationMode.NEGATIVE and not has_input(operation):
            # A rota sem entrada (o health check) tem uma requisição possível, e ela é válida.
            continue
        try:
            exercise(operation, MODES[kind])
        except Exception as error:  # a falha vira resultado, com a rota que a causou
            failures.append(f"{operation.label}: {error}")
    return failures


@then("nenhuma resposta foge do contrato")
def _(failures: list[str]) -> None:
    assert failures == [], "\n\n".join(failures)

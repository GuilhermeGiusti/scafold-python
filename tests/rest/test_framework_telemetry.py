import ast
from pathlib import Path

import pytest
from fastapi.telemetry import TelemetryConfig
from opentelemetry.sdk.trace import TracerProvider
from pytest_bdd import scenarios, then, when

from scafold.bootstrap.api import framework_telemetry
from scafold.bootstrap.telemetry import Telemetry

scenarios("rest/framework_telemetry.feature")

PROJECT = Path(__file__).resolve().parents[2]
SOURCES = (PROJECT / "src", PROJECT / "entrypoint")


@pytest.fixture
def telemetry() -> Telemetry:
    return Telemetry(meter_provider=None, tracer_provider=TracerProvider())


@when("procuro no código do projeto onde um app é criado", target_fixture="outcome")
def _() -> list[tuple[str, ast.Call]]:
    found: list[tuple[str, ast.Call]] = []
    for source in SOURCES:
        for path in source.rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "FastAPI":
                    found.append((str(path.relative_to(PROJECT)), node))
    return found


@then("todo app encontrado declara a telemetria do framework")
def _(outcome: list[tuple[str, ast.Call]]) -> None:
    assert outcome, "nenhuma chamada a FastAPI() encontrada: o cenário deixou de cobrir o projeto"
    without = [file for file, call in outcome if "telemetry" not in {kw.arg for kw in call.keywords}]
    assert without == []


@when(
    "leio a configuração que a montagem entrega ao framework com as métricas desligadas",
    target_fixture="outcome",
)
def _(telemetry: Telemetry) -> TelemetryConfig:
    return framework_telemetry(telemetry)


@then("o framework recebe o provider de traces da montagem")
def _(outcome: TelemetryConfig, telemetry: Telemetry) -> None:
    assert outcome.get("tracer_provider") is telemetry.tracer_provider


@then("as métricas, os logs e a leitura do ambiente do framework estão desligados")
def _(outcome: TelemetryConfig) -> None:
    assert (outcome.get("metrics"), outcome.get("logs"), outcome.get("auto_configure")) == (
        False,
        False,
        False,
    )

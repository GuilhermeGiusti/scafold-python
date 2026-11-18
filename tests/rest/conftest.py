"""O app da API sobre os fakes, com o Swagger ligado. Um ``Dado`` pode trocá-lo."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response
from opentelemetry.sdk.trace import TracerProvider
from pytest_bdd import parsers, then, when

from scafold.bootstrap.api import build_app
from scafold.bootstrap.telemetry import Telemetry

from ..support.scene import Scene


def build_test_app(scene: Scene, *, expose_docs: bool = True) -> FastAPI:
    telemetry = Telemetry(meter_provider=None, tracer_provider=TracerProvider())
    return build_app(use_cases=scene.use_cases, telemetry=telemetry, expose_docs=expose_docs)


@pytest.fixture
def app(scene: Scene) -> FastAPI:
    return build_test_app(scene)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    # `raise_server_exceptions=False`: o defeito chega ao cenário como o 500 que o cliente vê.
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@when(parsers.parse('acesso "{method} {path}"'), target_fixture="outcome")
def _(client: TestClient, method: str, path: str) -> Response:
    return client.request(method, path)


@when(
    parsers.parse('procuro a rota "{method} {path}" no documento OpenAPI da aplicação'),
    target_fixture="operation",
)
def _(app: FastAPI, method: str, path: str) -> object:
    return app.openapi()["paths"].get(path, {}).get(method.lower())


@then("a rota está documentada")
def _(operation: object) -> None:
    assert operation is not None

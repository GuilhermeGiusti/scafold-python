from fastapi import FastAPI
from pytest_bdd import given, parsers, scenarios

from scafold.bootstrap.settings import EXPOSE_DOCS_VARIABLE, switch

from ..support.scene import Scene
from .conftest import build_test_app

scenarios("rest/docs_exposure.feature")


@given(
    parsers.parse('o processo configurado com API_EXPOSE_DOCS igual a "{value}"'),
    target_fixture="app",
)
def _(scene: Scene, value: str) -> FastAPI:
    expose = switch({EXPOSE_DOCS_VARIABLE: value}, EXPOSE_DOCS_VARIABLE, default=False)
    return build_test_app(scene, expose_docs=expose)


@given("o processo configurado com nenhuma variável", target_fixture="app")
def _(scene: Scene) -> FastAPI:
    expose = switch({}, EXPOSE_DOCS_VARIABLE, default=False)
    return build_test_app(scene, expose_docs=expose)

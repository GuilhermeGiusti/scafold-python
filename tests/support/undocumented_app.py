"""Uma aplicação escrita do jeito errado, para provar que cada regra acusa quem a descumpre.

Uma rota está certa de propósito, `GET /loose/status`: ela prova que a regra do 422 não acusa
rota sem entrada.
"""

from fastapi import FastAPI
from pydantic import BaseModel

from scafold.infrastructure.rest.shared.error_presenter import ErrorPresenter


class LooseRequest(BaseModel):
    name: str
    amount: int


class LooseResponse(BaseModel):
    name: str


def build_undocumented_app() -> FastAPI:
    app = FastAPI()

    @app.post("/loose")
    async def loose(request: LooseRequest) -> LooseResponse:
        return LooseResponse(name=request.name)

    @app.get("/loose")
    async def untyped() -> dict[str, str]:
        return {}

    # Rota com entrada que não documenta o 422. O FastAPI acrescenta sozinho um 422 em toda rota
    # com entrada, a não ser que ela documente uma resposta genérica `default`, como esta.
    @app.get(
        "/loose/limited",
        responses={500: {"description": "Defeito."}, "default": {"description": "Outro erro."}},
    )
    async def limited(limit: int = 10) -> LooseResponse:
        return LooseResponse(name=str(limit))

    # Rota sem entrada: sem parâmetro nem corpo, não há o que recusar, e o 500 basta.
    @app.get("/loose/status", responses=ErrorPresenter.documented_errors(validation=False))
    async def status() -> LooseResponse:
        return LooseResponse(name="ok")

    return app

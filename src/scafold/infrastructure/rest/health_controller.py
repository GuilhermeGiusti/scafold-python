"""Controller REST do health check: o processo está de pé e atende requisições.

A rota não chama banco nem broker: responde 200 sempre que o processo atende. Ela segue as mesmas
regras de documentação de toda rota. Como não tem entrada, documenta só o 500
(``documented_errors(validation=False)``).
"""

from __future__ import annotations

from fastapi import APIRouter

from scafold.infrastructure.rest.health_schemas import HealthResponse
from scafold.infrastructure.rest.shared.error_presenter import ErrorPresenter

TAG = "health"


class HealthController:
    def __init__(self) -> None:
        self.router = APIRouter(tags=[TAG])
        self.router.add_api_route(
            "/health/check",
            self.check,
            methods=["GET"],
            summary="Confere se o processo está de pé",
            description="Responde 200 enquanto o processo atende requisições. "
            "Não consulta dependências.",
            response_model=HealthResponse,
            response_description="O processo está de pé.",
            responses=ErrorPresenter.documented_errors(validation=False),
        )

    async def check(self) -> HealthResponse:
        return HealthResponse(status="ok")

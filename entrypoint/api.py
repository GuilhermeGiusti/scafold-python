"""Ponto de entrada da API REST com FastAPI.

    uv run --env-file .env python entrypoint/api.py

A ordem do boot importa:

1. a configuração é lida e validada, antes de tudo. Uma recusa sai com código 1 e uma linha na
   saída de erro, que não é registro de log, porque o log ainda não existe;
2. o log estruturado é configurado, com o nível de ``LOG_DEBUG``;
3. a telemetria é montada;
4. a fundação e o app são montados, sem abrir conexão;
5. o servidor sobe. O Swagger fica em ``/docs`` quando ``API_EXPOSE_DOCS=true``.

O log de acesso do servidor fica desligado: ele escreve o caminho pedido com a query string, que é
dado da requisição. Quem registra a requisição é o span que o framework abre. No encerramento,
mesmo por erro, a telemetria pendente é enviada e o pool é fechado.
"""

import logging
import os
import sys
from collections.abc import Mapping

import uvicorn

from scafold.bootstrap.api import build_app
from scafold.bootstrap.composition import LOGGER_NAME, build_foundation
from scafold.bootstrap.settings import ConfigurationError, Settings
from scafold.bootstrap.telemetry import build_telemetry
from scafold.infrastructure.observability.json_log_formatter import configure_logging

HOST = "127.0.0.1"
PORT = 8000


def run(environment: Mapping[str, str]) -> int:
    """Lê a configuração e sobe o serviço. Devolve o código de saída do processo."""
    try:
        settings = Settings.from_environment(environment)
    except ConfigurationError as refusal:
        print(str(refusal), file=sys.stderr)
        return 1

    configure_logging(service=settings.service_name, level=settings.log_level)
    logger = logging.getLogger(LOGGER_NAME)
    telemetry = build_telemetry(settings)
    try:
        foundation = build_foundation(settings=settings, telemetry=telemetry)
        app = build_app(
            use_cases=foundation.use_cases,
            telemetry=telemetry,
            expose_docs=settings.expose_docs,
            on_shutdown=foundation.close,
        )
        # `log_config=None`: o servidor não troca o formatador JSON do logger raiz.
        uvicorn.run(app, host=HOST, port=PORT, access_log=False, log_config=None)
    except Exception:
        logger.exception("falha ao subir a api")
        return 1
    finally:
        telemetry.shutdown()
    return 0


def main() -> None:
    """O único ponto que toca ``os.environ``, e só para entregá-lo à configuração."""
    sys.exit(run(os.environ))


if __name__ == "__main__":
    main()

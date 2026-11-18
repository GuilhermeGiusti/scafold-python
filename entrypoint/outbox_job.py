"""Ponto de entrada do job da outbox: processo PRÓPRIO, nunca embutido na API (ADR-006).

    uv run --env-file .env python entrypoint/outbox_job.py

Subir o agendador dentro da API amarraria o ciclo de vida e a escala do job aos dela. Com mais de
uma Strategy, o mesmo arquivo roda em um container por Strategy, cada um com o seu
``OUTBOX_DISPATCHER``.

A ordem do boot:

1. configuração. Qualquer recusa sai com a mensagem e código 1, sem tocar banco nem broker;
2. log e telemetria;
3. ``broker.start()``: broker fora do ar aqui derruba o processo, de propósito, antes de o job se
   anunciar pronto. Broker que cai com o job rodando vira falha transitória;
4. o laço do cron, até o sinal de encerramento. O primeiro ciclo espera o primeiro disparo.
"""

import asyncio
import logging
import os
import signal
import sys
from collections.abc import Mapping

from scafold.bootstrap.composition import LOGGER_NAME
from scafold.bootstrap.job_settings import JobSettings
from scafold.bootstrap.outbox_job import build_outbox_job
from scafold.bootstrap.settings import ConfigurationError
from scafold.bootstrap.telemetry import Telemetry, build_telemetry
from scafold.infrastructure.observability.json_log_formatter import configure_logging

#: Sai quando o broker respondeu e o laço do cron vai começar.
READY_MARKER = "outbox: job pronto, aguardando os disparos do cron"

#: Os sinais que pedem encerramento. No Windows entra também o `SIGBREAK` (Ctrl+Break).
_SHUTDOWN_SIGNALS: tuple[signal.Signals, ...] = (signal.SIGINT, signal.SIGTERM) + (
    (signal.SIGBREAK,) if sys.platform == "win32" else ()
)


def run(environment: Mapping[str, str]) -> int:
    try:
        settings = JobSettings.from_environment(environment)
    except ConfigurationError as refusal:
        print(str(refusal), file=sys.stderr)
        return 1

    configure_logging(service=settings.service_name, level=settings.log_level)
    logger = logging.getLogger(LOGGER_NAME)
    telemetry = build_telemetry(settings)
    try:
        asyncio.run(serve(settings, telemetry))
    except Exception:
        logger.exception("falha no job da outbox")
        return 1
    finally:
        telemetry.shutdown()
    return 0


async def serve(settings: JobSettings, telemetry: Telemetry) -> None:
    """O boot inteiro num laço só: a conexão do broker e o pool do banco são os da drenagem."""
    stop = asyncio.Event()
    _install_signal_handlers(stop)
    job = build_outbox_job(settings, telemetry, stop=stop)
    try:
        await job.broker.start()
        job.logger.debug(READY_MARKER)
        await job.scheduler.run(job.drain.execute, stop)
    finally:
        await job.close()


def _install_signal_handlers(stop: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    for received in _SHUTDOWN_SIGNALS:
        try:
            loop.add_signal_handler(received, stop.set)
        except (NotImplementedError, RuntimeError, ValueError):
            # Windows não implementa `add_signal_handler`; vale o tratador clássico.
            signal.signal(received, lambda *_: loop.call_soon_threadsafe(stop.set))


def main() -> None:
    sys.exit(run(os.environ))


if __name__ == "__main__":
    main()

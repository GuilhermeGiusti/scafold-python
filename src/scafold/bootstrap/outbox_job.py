"""A montagem do job da outbox, uma vez por processo (ADR-006).

Monta, a partir de ``JobSettings`` e da telemetria do processo, tudo o que a drenagem usa: os
adaptadores de métricas, a camada de dados, o observador de use case, a Strategy do broker com o
envoltório que abre o span de envio, o repositório da fila e o agendador. Usa as mesmas peças da
montagem da API, sem nenhuma borda HTTP: o job é um processo próprio e não expõe porta.

**Montar não conecta.** Quem conecta o broker é o ponto de entrada, com ``broker.start()``: broker
fora do ar no boot derruba o processo antes de ele se anunciar pronto.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

from scafold.applications.commands.drain_result import DrainResult
from scafold.applications.shared.use_case import AsyncNullaryUseCase
from scafold.applications.usecases.outbox_drain_use_case import OutboxDrainUseCase
from scafold.bootstrap.composition import LOGGER_NAME, build_metrics_adapters
from scafold.bootstrap.job_settings import JobSettings
from scafold.bootstrap.telemetry import Telemetry
from scafold.domain.outbox.dispatchers import KNOWN_DISPATCHERS
from scafold.infrastructure.brokers.rabbitmq_dispatcher import RabbitmqDispatcher
from scafold.infrastructure.observability.async_observed_use_cases import (
    AsyncObservedNullaryUseCase,
)
from scafold.infrastructure.observability.traced_dispatcher import TracedDispatcher
from scafold.infrastructure.observability.use_case_observer import UseCaseObserver
from scafold.infrastructure.persistence.outbox.sql_outbox_repository import SqlOutboxRepository
from scafold.infrastructure.persistence.persistence import Persistence, open_persistence
from scafold.infrastructure.scheduling.cron_scheduler import (
    Clock,
    CronScheduler,
    Waiter,
    utc_now,
    wait_or_stop,
)

#: O nome da drenagem nas métricas, nos spans e no log.
DRAIN_USE_CASE = "outbox_drain"


@dataclass(frozen=True, slots=True, kw_only=True)
class OutboxJob:
    """O que a montagem entrega ao ponto de entrada do job."""

    settings: JobSettings
    logger: logging.Logger
    persistence: Persistence
    #: A Strategy concreta, para o ponto de entrada conectar e desconectar.
    broker: RabbitmqDispatcher
    #: A drenagem já envolvida pela observação padrão de use case.
    drain: AsyncNullaryUseCase[DrainResult]
    scheduler: CronScheduler
    #: O pedido de parada, marcado pelos tratadores de sinal.
    stop: asyncio.Event

    async def close(self) -> None:
        """Fecha o broker e o pool, no mesmo event loop que os abriu."""
        await self.broker.close()
        await self.persistence.close()


def build_outbox_job(
    settings: JobSettings,
    telemetry: Telemetry,
    *,
    stop: asyncio.Event,
    now: Clock = utc_now,
    wait: Waiter = wait_or_stop,
) -> OutboxJob:
    """Monta o job sem abrir conexão. ``now`` e ``wait`` controlam o tempo nos testes."""
    logger = logging.getLogger(LOGGER_NAME)
    metrics = build_metrics_adapters(telemetry.meter_provider, logger)
    persistence = open_persistence(
        settings.database_url, metrics.persistence, telemetry.tracer_provider
    )
    observer = UseCaseObserver(
        metrics=metrics.use_case, logger=logger, tracer_provider=telemetry.tracer_provider
    )
    broker = RabbitmqDispatcher(settings.rabbitmq_url)
    drain = OutboxDrainUseCase(
        unit_of_work=persistence.unit_of_work,
        repository=SqlOutboxRepository(persistence.unit_of_work),
        # O span de cada envio é aberto pelo envoltório, por fora da Strategy e da drenagem.
        dispatcher=TracedDispatcher(broker, tracer_provider=telemetry.tracer_provider),
        metrics=metrics.outbox,
        batch_size=settings.batch_size,
        retry_countdown_seconds=settings.retry_countdown_seconds,
        stop_requested=stop.is_set,
        known_dispatchers=KNOWN_DISPATCHERS,
        logger=logger,
        clock=time.monotonic,
    )
    return OutboxJob(
        settings=settings,
        logger=logger,
        persistence=persistence,
        broker=broker,
        drain=AsyncObservedNullaryUseCase(drain, use_case=DRAIN_USE_CASE, observer=observer),
        scheduler=CronScheduler(settings.cron_schedule, logger=logger, now=now, wait=wait),
        stop=stop,
    )

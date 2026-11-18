"""O laço do agendador do job: disparos por expressão cron, um ciclo por vez.

O ``croniter`` só calcula o próximo disparo; o laço é do projeto (ADR-006). A expressão tem cinco
campos e é avaliada em UTC. O primeiro ciclo espera o primeiro disparo: o job não drena no boot.

**Não há dois ciclos ao mesmo tempo, por construção.** O laço aguarda o ciclo terminar antes de
calcular o próximo disparo. O disparo que caiu durante o ciclo é pulado, com um WARNING.

**Um ciclo que falha não derruba o job.** A falha vira ERROR, e o próximo disparo tenta de novo. O
cancelamento não é falha: ele sobe.

**A espera termina antes quando a parada é pedida.** O relógio e a espera entram por construtor,
para os testes controlarem o tempo.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from croniter import croniter

#: O relógio do agendador.
type Clock = Callable[[], datetime]

#: A espera até o próximo disparo, que termina antes se a parada for pedida.
type Waiter = Callable[[asyncio.Event, float], Awaitable[None]]

#: Um ciclo do job: a drenagem, chamada a cada disparo.
type Cycle = Callable[[], Awaitable[object]]

SKIPPED_MESSAGE = "outbox: disparo do cron pulado; disparos_pulados=%d"
FAILED_MESSAGE = "outbox: o ciclo falhou; o proximo tenta de novo"


def utc_now() -> datetime:
    return datetime.now(UTC)


async def wait_or_stop(stop: asyncio.Event, seconds: float) -> None:
    """Espera ``seconds`` ou até a parada, o que vier primeiro."""
    try:
        await asyncio.wait_for(stop.wait(), timeout=seconds)
    except TimeoutError:
        return


class CronScheduler:
    """Roda ciclos nos disparos de uma expressão cron, até a parada."""

    def __init__(
        self,
        expression: str,
        *,
        logger: logging.Logger,
        now: Clock = utc_now,
        wait: Waiter = wait_or_stop,
    ) -> None:
        self._expression = expression
        self._log = logger
        self._now = now
        self._wait = wait

    async def run(self, cycle: Cycle, stop: asyncio.Event) -> None:
        """Espera cada disparo, roda o ciclo e pula os disparos que caíram durante ele."""
        schedule = croniter(self._expression, self._now())
        next_fire: datetime = schedule.get_next(datetime)
        while not stop.is_set():
            remaining = (next_fire - self._now()).total_seconds()
            if remaining > 0:
                await self._wait(stop, remaining)
                continue
            await self._run_one(cycle)
            finished = self._now()
            next_fire = schedule.get_next(datetime)
            skipped = 0
            while next_fire <= finished:
                skipped += 1
                next_fire = schedule.get_next(datetime)
            if skipped:
                self._log.warning(SKIPPED_MESSAGE, skipped)

    async def _run_one(self, cycle: Cycle) -> None:
        try:
            await cycle()
        except asyncio.CancelledError:
            raise
        except Exception:
            self._log.exception(FAILED_MESSAGE)

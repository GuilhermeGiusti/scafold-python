import asyncio
import logging
from datetime import datetime, timedelta

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from scafold.infrastructure.scheduling.cron_scheduler import (
    FAILED_MESSAGE,
    SKIPPED_MESSAGE,
    CronScheduler,
)

from ..conftest import Run

scenarios("infrastructure/cron_scheduler.feature")

LOGGER = "scafold.scheduler.test"


class FakeTime:
    """O relógio do agendador: a espera avança o tempo em vez de dormir."""

    def __init__(self, start: datetime) -> None:
        self.now = start

    def clock(self) -> datetime:
        return self.now

    async def wait(self, stop: asyncio.Event, seconds: float) -> None:
        self.now += timedelta(seconds=seconds)


@pytest.fixture
def failing_first() -> bool:
    return False


@given(parsers.parse('o relógio do agendador em "{instant}"'), target_fixture="fake_time")
def _(instant: str) -> FakeTime:
    return FakeTime(datetime.fromisoformat(instant))


@given("o primeiro ciclo falhando", target_fixture="failing_first")
def _() -> bool:
    return True


@when(
    parsers.parse('o agendador "{expression}" roda {cycles:d} ciclos de {seconds:d} segundos')
)
@when(
    parsers.parse('o agendador "{expression}" roda {cycles:d} ciclos de {seconds:d} segundo'),
)
def _(
    run: Run,
    fake_time: FakeTime,
    failing_first: bool,
    runs: list[datetime],
    expression: str,
    cycles: int,
    seconds: int,
) -> None:
    stop = asyncio.Event()

    async def cycle() -> None:
        runs.append(fake_time.now)
        fake_time.now += timedelta(seconds=seconds)
        if len(runs) >= cycles:
            stop.set()
        if failing_first and len(runs) == 1:
            raise RuntimeError("banco fora do ar")

    scheduler = CronScheduler(
        expression, logger=logging.getLogger(LOGGER), now=fake_time.clock, wait=fake_time.wait
    )
    run(scheduler.run(cycle, stop))


@pytest.fixture
def runs() -> list[datetime]:
    return []


@then(parsers.parse('os ciclos rodaram em "{times}"'))
def _(runs: list[datetime], times: str) -> None:
    assert [moment.strftime("%H:%M:%S") for moment in runs] == times.split(", ")


@then(parsers.parse("a cada ciclo o agendador avisou que pulou {skipped:d} disparos"))
def _(caplog: pytest.LogCaptureFixture, runs: list[datetime], skipped: int) -> None:
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert warnings == [SKIPPED_MESSAGE % skipped] * len(runs)


@then("o agendador registrou a falha do ciclo")
def _(caplog: pytest.LogCaptureFixture) -> None:
    errors = [record for record in caplog.records if record.levelno == logging.ERROR]
    assert [record.getMessage() for record in errors] == [FAILED_MESSAGE]
    assert errors[0].exc_info is not None

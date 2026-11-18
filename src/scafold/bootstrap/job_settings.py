"""Configuração do job da outbox, lida do ambiente uma vez, no boot.

É um objeto próprio, e não ``Settings`` acrescido de campos: a API não lê as variáveis do job, e o
job não lê as que só a API usa (``API_EXPOSE_DOCS``). As variáveis compartilhadas têm o mesmo nome
de campo e passam pelas mesmas funções de regra de ``settings.py``, com as mesmas mensagens.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from croniter import croniter

from scafold.bootstrap.settings import (
    LOG_DEBUG_VARIABLE,
    METRICS_ENABLED_VARIABLE,
    SERVICE_NAME_VARIABLE,
    TRACES_ENABLED_VARIABLE,
    ConfigurationError,
    database_url,
    log_level,
    optional,
    otlp_endpoints,
    outbox_dispatcher,
    positive_integer,
    required,
    switch,
)

RABBITMQ_URL_VARIABLE = "RABBITMQ_URL"
OUTBOX_CRON_SCHEDULE_VARIABLE = "OUTBOX_CRON_SCHEDULE"
OUTBOX_BATCH_SIZE_VARIABLE = "OUTBOX_BATCH_SIZE"
OUTBOX_RETRY_COUNTDOWN_VARIABLE = "OUTBOX_RETRY_COUNTDOWN"

DEFAULT_CRON_SCHEDULE = "* * * * *"
DEFAULT_BATCH_SIZE = 1000
DEFAULT_RETRY_COUNTDOWN_SECONDS = 30

#: Minuto, hora, dia do mês, mês e dia da semana. O campo de segundos é recusado.
CRON_FIELDS = 5

_RABBITMQ_SCHEMES = ("amqp", "amqps")


@dataclass(frozen=True, slots=True, kw_only=True)
class JobSettings:
    """A configuração inteira do job, imutável. Cumpre ``TelemetrySettings``."""

    service_name: str
    metrics_enabled: bool
    traces_enabled: bool
    metrics_endpoint: str
    traces_endpoint: str
    log_debug: bool
    database_url: str = field(repr=False)
    outbox_dispatcher: str
    rabbitmq_url: str = field(repr=False)
    cron_schedule: str
    batch_size: int
    retry_countdown_seconds: int

    @property
    def log_level(self) -> int:
        return log_level(self.log_debug)

    @classmethod
    def from_environment(cls, environment: Mapping[str, str]) -> JobSettings:
        metrics_endpoint, traces_endpoint = otlp_endpoints(environment)
        return cls(
            service_name=required(environment, SERVICE_NAME_VARIABLE),
            metrics_enabled=switch(environment, METRICS_ENABLED_VARIABLE, default=True),
            traces_enabled=switch(environment, TRACES_ENABLED_VARIABLE, default=True),
            metrics_endpoint=metrics_endpoint,
            traces_endpoint=traces_endpoint,
            log_debug=switch(environment, LOG_DEBUG_VARIABLE, default=False),
            database_url=database_url(environment),
            outbox_dispatcher=outbox_dispatcher(environment),
            rabbitmq_url=rabbitmq_url(environment),
            cron_schedule=cron_schedule(environment),
            batch_size=positive_integer(
                environment, OUTBOX_BATCH_SIZE_VARIABLE, default=DEFAULT_BATCH_SIZE
            ),
            retry_countdown_seconds=positive_integer(
                environment,
                OUTBOX_RETRY_COUNTDOWN_VARIABLE,
                default=DEFAULT_RETRY_COUNTDOWN_SECONDS,
            ),
        )


def rabbitmq_url(environment: Mapping[str, str]) -> str:
    value = required(environment, RABBITMQ_URL_VARIABLE)
    if urlsplit(value).scheme.lower() not in _RABBITMQ_SCHEMES:
        raise ConfigurationError(f"{RABBITMQ_URL_VARIABLE} aceita amqp:// ou amqps://.")
    return value


def is_valid_cron(expression: str) -> bool:
    """Uma expressão cron válida de cinco campos, sem segundos."""
    return len(expression.split()) == CRON_FIELDS and croniter.is_valid(expression)


def cron_schedule(environment: Mapping[str, str]) -> str:
    value = optional(environment, OUTBOX_CRON_SCHEDULE_VARIABLE)
    if value is None:
        return DEFAULT_CRON_SCHEDULE
    if not is_valid_cron(value):
        raise ConfigurationError(
            f"{OUTBOX_CRON_SCHEDULE_VARIABLE} aceita uma expressão cron de cinco campos."
        )
    return value

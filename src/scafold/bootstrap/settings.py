"""Configuração do processo, lida do ambiente uma vez, no boot.

Tudo o que o processo precisa saber vem daqui e segue por parâmetro. Nenhum outro código lê variável
de ambiente: o ponto de entrada entrega ``os.environ`` a ``Settings.from_environment`` e o resto
recebe ``Settings``. Assim um teste monta a configuração que quiser passando um dicionário.

**Cada sinal de telemetria tem a sua variável, e os dois nascem LIGADOS.** Produção não fica sem
métrica por esquecimento.

**``LOG_DEBUG`` nasce desligada.** Por padrão o log só mostra WARNING e ERROR; com ``true``, mostra
tudo, a partir de DEBUG. Os registros de rotina (início e fim de use case, medições escritas no
log) saem em DEBUG.

**Só ``true`` e ``false`` são aceitos nos interruptores.** Um ``0`` ou ``True`` é recusado em vez de
ser adivinhado. **A recusa nunca repete o valor recebido**: uma ``DATABASE_URL`` inválida costuma
trazer senha.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from scafold.domain.outbox.dispatchers import KNOWN_DISPATCHERS

SERVICE_NAME_VARIABLE = "OTEL_SERVICE_NAME"
METRICS_ENABLED_VARIABLE = "TELEMETRY_METRICS_ENABLED"
TRACES_ENABLED_VARIABLE = "TELEMETRY_TRACES_ENABLED"
OTLP_ENDPOINT_VARIABLE = "OTEL_EXPORTER_OTLP_ENDPOINT"
OTLP_METRICS_ENDPOINT_VARIABLE = "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT"
OTLP_TRACES_ENDPOINT_VARIABLE = "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"
DATABASE_URL_VARIABLE = "DATABASE_URL"

#: Liga a tela do Swagger e o `openapi.json`. Desligada por padrão: produção não precisa lembrar
#: de desligar. O documento existe sempre; só a exposição depende da variável.
EXPOSE_DOCS_VARIABLE = "API_EXPOSE_DOCS"

#: Liga o log de tudo, a partir de DEBUG. Desligada, só WARNING e ERROR aparecem.
LOG_DEBUG_VARIABLE = "LOG_DEBUG"

#: O carimbo das mensagens novas da outbox (ADR-006).
OUTBOX_DISPATCHER_VARIABLE = "OUTBOX_DISPATCHER"

#: O endereço base quando nenhuma variável o define. É o padrão do OpenTelemetry para OTLP/HTTP.
DEFAULT_OTLP_ENDPOINT = "http://localhost:4318"

#: O nível do log sem `LOG_DEBUG`: erro e aviso.
DEFAULT_LOG_LEVEL = logging.WARNING

#: O nível do log com `LOG_DEBUG=true`: tudo.
DEBUG_LOG_LEVEL = logging.DEBUG

#: O único esquema aceito. Quem escolhe o driver é a camada de dados.
DATABASE_SCHEME = "postgresql://"

_METRICS_PATH = "/v1/metrics"
_TRACES_PATH = "/v1/traces"


class ConfigurationError(ValueError):
    """Variável de ambiente ausente ou com valor fora do contrato. Recusa o boot."""


class TelemetrySettings(Protocol):
    """O que a montagem da telemetria lê. ``Settings`` e ``JobSettings`` cumprem."""

    @property
    def service_name(self) -> str: ...

    @property
    def metrics_enabled(self) -> bool: ...

    @property
    def traces_enabled(self) -> bool: ...

    @property
    def metrics_endpoint(self) -> str: ...

    @property
    def traces_endpoint(self) -> str: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class Settings:
    """A configuração da API, da CLI e da tela Streamlit, imutável.

    ``database_url`` fica fora do ``repr``: o objeto pode aparecer num traceback ou num log.
    """

    service_name: str
    metrics_enabled: bool
    traces_enabled: bool
    metrics_endpoint: str
    traces_endpoint: str
    expose_docs: bool
    log_debug: bool
    database_url: str = field(repr=False)
    outbox_dispatcher: str

    @property
    def log_level(self) -> int:
        return log_level(self.log_debug)

    @classmethod
    def from_environment(cls, environment: Mapping[str, str]) -> Settings:
        metrics_endpoint, traces_endpoint = otlp_endpoints(environment)
        return cls(
            service_name=required(environment, SERVICE_NAME_VARIABLE),
            metrics_enabled=switch(environment, METRICS_ENABLED_VARIABLE, default=True),
            traces_enabled=switch(environment, TRACES_ENABLED_VARIABLE, default=True),
            metrics_endpoint=metrics_endpoint,
            traces_endpoint=traces_endpoint,
            expose_docs=switch(environment, EXPOSE_DOCS_VARIABLE, default=False),
            log_debug=switch(environment, LOG_DEBUG_VARIABLE, default=False),
            database_url=database_url(environment),
            outbox_dispatcher=outbox_dispatcher(environment),
        )


def log_level(log_debug: bool) -> int:
    """DEBUG com ``LOG_DEBUG=true``; senão, WARNING, que mostra aviso e erro."""
    return DEBUG_LOG_LEVEL if log_debug else DEFAULT_LOG_LEVEL


def optional(environment: Mapping[str, str], variable: str) -> str | None:
    """O valor da variável, ou ``None`` quando ela está ausente ou só tem espaços."""
    value = environment.get(variable, "").strip()
    return value or None


def required(environment: Mapping[str, str], variable: str) -> str:
    value = optional(environment, variable)
    if value is None:
        raise ConfigurationError(f"{variable} é obrigatória.")
    return value


def switch(environment: Mapping[str, str], variable: str, *, default: bool) -> bool:
    """Um interruptor. Só ``true`` e ``false``, em minúsculas."""
    value = optional(environment, variable)
    if value is None:
        return default
    if value == "true":
        return True
    if value == "false":
        return False
    raise ConfigurationError(f"{variable} aceita true ou false.")


def otlp_endpoints(environment: Mapping[str, str]) -> tuple[str, str]:
    """Os endereços das métricas e dos traces. O endereço de um sinal vence o endereço base."""
    base = (optional(environment, OTLP_ENDPOINT_VARIABLE) or DEFAULT_OTLP_ENDPOINT).rstrip("/")
    return (
        optional(environment, OTLP_METRICS_ENDPOINT_VARIABLE) or base + _METRICS_PATH,
        optional(environment, OTLP_TRACES_ENDPOINT_VARIABLE) or base + _TRACES_PATH,
    )


def database_url(environment: Mapping[str, str]) -> str:
    value = required(environment, DATABASE_URL_VARIABLE)
    if not value.startswith(DATABASE_SCHEME):
        raise ConfigurationError(f"{DATABASE_URL_VARIABLE} aceita apenas o esquema {DATABASE_SCHEME}.")
    return value


def outbox_dispatcher(environment: Mapping[str, str]) -> str:
    """O carimbo da outbox, comparado exatamente, como o ``CHECK`` do banco."""
    value = required(environment, OUTBOX_DISPATCHER_VARIABLE)
    if value not in KNOWN_DISPATCHERS:
        raise ConfigurationError(
            f"{OUTBOX_DISPATCHER_VARIABLE} aceita {' | '.join(KNOWN_DISPATCHERS)}."
        )
    return value


def positive_integer(environment: Mapping[str, str], variable: str, *, default: int) -> int:
    """Um inteiro maior que zero, ou o padrão quando ausente."""
    value = optional(environment, variable)
    if value is None:
        return default
    if not value.isascii() or not value.isdigit() or int(value) < 1:
        raise ConfigurationError(f"{variable} aceita um inteiro positivo.")
    return int(value)

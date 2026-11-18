import logging

from pytest_bdd import given, parsers, scenarios, then, when

from scafold.bootstrap.settings import (
    DATABASE_URL_VARIABLE,
    OUTBOX_DISPATCHER_VARIABLE,
    SERVICE_NAME_VARIABLE,
    ConfigurationError,
    Settings,
)

scenarios("bootstrap/settings.feature")


@given(
    "o ambiente com o nome do serviço, a URL do banco e o carimbo da outbox",
    target_fixture="environment",
)
def _() -> dict[str, str]:
    return {
        SERVICE_NAME_VARIABLE: "scafold-test",
        DATABASE_URL_VARIABLE: "postgresql://app:segredo@localhost:5432/app",
        OUTBOX_DISPATCHER_VARIABLE: "rabbitmq",
    }


@given(parsers.parse('a variável "{name}" igual a "{value}"'))
def _(environment: dict[str, str], name: str, value: str) -> None:
    environment[name] = value


@given(parsers.parse('o ambiente sem a variável "{name}"'))
def _(environment: dict[str, str], name: str) -> None:
    del environment[name]


@when("a configuração é lida", target_fixture="outcome")
def _(environment: dict[str, str]) -> Settings | ConfigurationError:
    try:
        return Settings.from_environment(environment)
    except ConfigurationError as error:  # só o erro esperado vira resultado
        return error


@then(parsers.parse('o nível do log é "{level}"'))
def _(outcome: Settings | ConfigurationError, level: str) -> None:
    assert isinstance(outcome, Settings)
    assert logging.getLevelName(outcome.log_level) == level


@then(parsers.parse('a recusa cita a variável "{name}" sem repetir "{value}"'))
def _(outcome: Settings | ConfigurationError, name: str, value: str) -> None:
    assert isinstance(outcome, ConfigurationError)
    assert name in str(outcome)
    assert value not in str(outcome).removeprefix(name)


@then("o envio de métricas e o de traces ficam ligados")
def _(outcome: Settings | ConfigurationError) -> None:
    assert isinstance(outcome, Settings)
    assert (outcome.metrics_enabled, outcome.traces_enabled) == (True, True)


@then("o Swagger fica desligado")
def _(outcome: Settings | ConfigurationError) -> None:
    assert isinstance(outcome, Settings)
    assert outcome.expose_docs is False

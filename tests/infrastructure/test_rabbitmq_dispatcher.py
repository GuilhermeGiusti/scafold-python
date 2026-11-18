from collections.abc import Iterator
from uuid import uuid4

import aio_pika
import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from testcontainers.community.rabbitmq import RabbitMqContainer

from scafold.domain.outbox.dispatchers import RABBITMQ_DISPATCHER
from scafold.domain.outbox.value_objects.dispatch_outcome import DispatchOutcome
from scafold.domain.outbox.value_objects.pending_message import PendingMessage
from scafold.domain.outbox.value_objects.permanent_failure import PermanentFailure
from scafold.domain.outbox.value_objects.published import Published
from scafold.domain.outbox.value_objects.transient_failure import TransientFailure
from scafold.infrastructure.brokers.rabbitmq_dispatcher import RabbitmqDispatcher

from ..conftest import Run

scenarios("infrastructure/rabbitmq_dispatcher.feature")

RABBITMQ_IMAGE = "rabbitmq:4.3-management-alpine"
QUEUE = "example.audit"

KINDS: dict[str, type[DispatchOutcome]] = {
    "publicada": Published,
    "falha transitória": TransientFailure,
    "falha permanente": PermanentFailure,
}


@pytest.fixture(scope="session")
def rabbitmq_url() -> Iterator[str]:
    """Um RabbitMQ por sessão. Pedir esta fixture é o que exige Docker."""
    with RabbitMqContainer(RABBITMQ_IMAGE) as container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(container.port)
        yield f"amqp://{container.username}:{container.password}@{host}:{port}/"


def message(destination: str) -> PendingMessage:
    return PendingMessage(
        id=uuid4(),
        destination=destination,
        event_type="example.created",
        event_version=1,
        payload={"id": "1"},
        aggregate_type="example",
        aggregate_id="1",
        correlation_id="0" * 32,
        trace_context=None,
        dispatcher=RABBITMQ_DISPATCHER,
        attempts=0,
        routing_key="example.created",
    )


@given(parsers.parse('o RabbitMQ com a exchange "{exchange}" ligada a uma fila'))
def _(run: Run, rabbitmq_url: str, exchange: str) -> None:
    async def declare() -> None:
        connection = await aio_pika.connect(rabbitmq_url)
        async with connection:
            channel = await connection.channel()
            declared = await channel.declare_exchange(
                exchange, aio_pika.ExchangeType.TOPIC, durable=True
            )
            queue = await channel.declare_queue(QUEUE, durable=True)
            await queue.purge()
            await queue.bind(declared, routing_key="#")

    run(declare())


@when(
    parsers.parse('a Strategy publica uma mensagem para o destino "{destination}"'),
    target_fixture="outcome",
)
def _(run: Run, rabbitmq_url: str, destination: str) -> DispatchOutcome:
    async def publish() -> DispatchOutcome:
        dispatcher = RabbitmqDispatcher(rabbitmq_url)
        await dispatcher.start()
        try:
            return await dispatcher.dispatch(message(destination))
        finally:
            await dispatcher.close()

    outcome: DispatchOutcome = run(publish())
    return outcome


@then(parsers.parse('o resultado é "{kind}"'))
def _(outcome: DispatchOutcome, kind: str) -> None:
    assert type(outcome) is KINDS[kind], outcome


@then(parsers.parse('a fila recebeu a mensagem com o cabeçalho "{header}"'))
def _(run: Run, rabbitmq_url: str, header: str) -> None:
    async def receive() -> object:
        connection = await aio_pika.connect(rabbitmq_url)
        async with connection:
            channel = await connection.channel()
            queue = await channel.get_queue(QUEUE)
            received = await queue.get(timeout=5)
            await received.ack()
            return received.headers.get(header)

    assert run(receive())

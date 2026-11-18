"""Strategy de publicação para RabbitMQ. Cumpre ``IDispatcher`` (ADR-006).

Duas opções do cliente são obrigatórias, e não preferência:

- **``mandatory=True`` mais ``on_return_raises=True``**: sem o primeiro, o broker descarta a mensagem
  não roteável em silêncio; sem o segundo, o ``publish`` volta com sucesso assim mesmo, e a mensagem
  seria marcada como publicada sem ter ido a lugar nenhum.
- **Publisher confirms**: sem eles, ``Published`` significaria "escrevi no socket", e não "o broker
  aceitou".

``connect_robust`` levanta quando o broker está fora no primeiro connect (o job não sobe) e
reconecta sozinho quando o broker cai com o job rodando (aí a falha vira transitória).

**A confirmação tem prazo** (``CONFIRM_TIMEOUT_SECONDS``): um broker degradado que aceita a conexão
e nunca confirma prenderia o ciclo inteiro.

**A exchange é declarada de forma passiva**: exchange inexistente vira falha permanente, em vez de
ser criada por acidente pelo produtor. Quem declara a topologia é a infraestrutura do ambiente.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aio_pika
from aio_pika.abc import AbstractExchange, AbstractRobustChannel, AbstractRobustConnection

from scafold.domain.outbox.dispatchers import RABBITMQ_DISPATCHER
from scafold.domain.outbox.value_objects.dispatch_outcome import DispatchOutcome
from scafold.domain.outbox.value_objects.pending_message import PendingMessage
from scafold.domain.outbox.value_objects.permanent_failure import PermanentFailure
from scafold.domain.outbox.value_objects.published import Published
from scafold.domain.outbox.value_objects.transient_failure import TransientFailure

#: Erros que NÃO melhoram com retentativa. Checados PRIMEIRO: os erros de autenticação do aio-pika
#: herdam de `ConnectionError`, e uma cláusula transiente antes desta os capturaria.
_PERMANENT = (
    aio_pika.exceptions.DeliveryError,  # devolvida: não roteável
    aio_pika.exceptions.ChannelNotFoundEntity,  # exchange inexistente (404)
    aio_pika.exceptions.ChannelPreconditionFailed,
    aio_pika.exceptions.AuthenticationError,
    aio_pika.exceptions.ProbableAuthenticationError,
)

#: Erros que podem passar na próxima. Tudo o que não estiver aqui nem acima TAMBÉM é transiente:
#: errar para transiente custa cinco tentativas; errar para permanente MATA a mensagem.
_TRANSIENT = (
    aio_pika.exceptions.AMQPConnectionError,
    aio_pika.exceptions.ChannelInvalidStateError,
    ConnectionError,
    OSError,
)

#: `ACCESS_REFUSED` do AMQP. Chega como `ChannelClosed`, que de resto é transiente.
_ACCESS_REFUSED = 403

#: O prazo da confirmação do broker, em segundos.
CONFIRM_TIMEOUT_SECONDS = 10.0

#: A linha que o job escreve ao conectar e a cada reconexão.
CONNECTED_LOG_MESSAGE = "outbox: conectado ao RabbitMQ"

#: O tamanho máximo do detalhe gravado em `outbox_error`.
_DETAIL_LIMIT = 500

_logger = logging.getLogger(__name__)


class RabbitmqDispatcher:
    """``destination`` é o nome lógico do alvo; aqui ele vira a exchange."""

    def __init__(self, url: str) -> None:
        self._url = url
        self._connection: AbstractRobustConnection | None = None
        self._channel: AbstractRobustChannel | None = None

    @property
    def name(self) -> str:
        return RABBITMQ_DISPATCHER

    async def start(self) -> None:
        """Conecta. Broker fora do ar aqui derruba o processo: a exceção sobe."""
        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel(
            publisher_confirms=True, on_return_raises=True
        )
        self._connection.reconnect_callbacks.add(self._announce_connection)
        self._announce_connection(self._connection)

    def _announce_connection(self, connection: object) -> None:
        _logger.debug(CONNECTED_LOG_MESSAGE)

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
            self._channel = None

    async def dispatch(self, message: PendingMessage) -> DispatchOutcome:
        """Publica e relata. NUNCA levanta."""
        try:
            exchange = await self._exchange(message.destination)
            await asyncio.wait_for(
                exchange.publish(
                    self._envelope(message),
                    # Lida CONGELADA da linha; o tipo do evento é só o padrão da gravação.
                    routing_key=message.routing_key or message.event_type,
                    mandatory=True,
                ),
                timeout=CONFIRM_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            return TransientFailure(f"o RabbitMQ nao confirmou em {CONFIRM_TIMEOUT_SECONDS:g}s")
        except _PERMANENT as failure:
            return PermanentFailure(_describe(failure))
        except aio_pika.exceptions.ChannelClosed as failure:
            # Permissão negada é permanente; canal fechado por outro motivo, transiente.
            if getattr(failure, "reply_code", None) == _ACCESS_REFUSED:
                return PermanentFailure(_describe(failure))
            return TransientFailure(_describe(failure))
        except _TRANSIENT as failure:
            return TransientFailure(_describe(failure))
        except Exception as failure:  # a regra de ouro: desconhecido é transiente
            return TransientFailure(_describe(failure))
        return Published()

    async def _exchange(self, name: str) -> AbstractExchange:
        if self._channel is None:
            raise aio_pika.exceptions.ChannelInvalidStateError("dispatcher nao foi iniciado")
        # `ensure=True` faz a declaração PASSIVA: exchange inexistente vira erro.
        return await self._channel.get_exchange(name, ensure=True)

    def _envelope(self, message: PendingMessage) -> aio_pika.Message:
        headers: dict[str, Any] = {
            # A chave de idempotência do consumidor. Única âncora estável entre tentativas.
            "message_id": str(message.id),
            "event_type": message.event_type,
            "event_version": int(message.event_version),
            "correlation_id": message.correlation_id,
            "aggregate_type": message.aggregate_type,
            "aggregate_id": message.aggregate_id,
        }
        if message.trace_context:
            headers["traceparent"] = message.trace_context
        return aio_pika.Message(
            body=json.dumps(message.payload, ensure_ascii=False).encode("utf-8"),
            content_type="application/json",
            message_id=str(message.id),
            correlation_id=message.correlation_id,
            headers=headers,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )


def _describe(failure: BaseException) -> str:
    """O detalhe vai para `outbox_error`, e NUNCA o payload."""
    return f"{type(failure).__name__}: {failure}"[:_DETAIL_LIMIT]

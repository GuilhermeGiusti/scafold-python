"""A mensagem reivindicada pela drenagem, com os dados de envio congelados na gravação."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class PendingMessage:
    """Uma linha de ``outbox_message`` pronta para sair.

    ``routing_key`` vem da tabela de dados de envio do RabbitMQ e nunca é recalculada no envio:
    mudar a regra de derivação transformaria uma mensagem já aceita numa duplicata.
    """

    #: O `message_id` publicado, chave de idempotência do consumidor.
    id: UUID
    destination: str
    event_type: str
    event_version: int
    payload: Mapping[str, Any]
    aggregate_type: str
    aggregate_id: str
    correlation_id: str
    #: O `traceparent` W3C do produtor, quando gravado.
    trace_context: str | None
    dispatcher: str
    #: As falhas já registradas para a mensagem.
    attempts: int
    routing_key: str | None

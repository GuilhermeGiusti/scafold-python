"""O evento de integração: tudo o que o produtor entrega ao gravador da outbox."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from scafold.domain.outbox.errors.invalid_integration_event import InvalidIntegrationEvent

#: O destino lógico vira o nome do alvo no broker (a exchange, no RabbitMQ). Letras ASCII,
#: números, ponto, hífen e sublinhado, com até 255 caracteres.
DESTINATION_PATTERN = re.compile(r"[A-Za-z0-9_.-]{1,255}")


@dataclass(frozen=True, slots=True, kw_only=True)
class IntegrationEvent:
    """Um evento que SAI do processo, ao contrário do evento de domínio, que fica nele.

    ``destination`` é o nome lógico do alvo, nunca uma exchange, um tópico ou um ARN escolhido
    pelo produtor: quem traduz para o alvo real é a Strategy, no envio. ``routing_key`` é
    opcional; vazia, o gravador usa o tipo do evento. O valor fica congelado na linha, e a
    identidade que o broker enxerga não muda entre tentativas.
    """

    destination: str
    event_type: str
    event_version: int
    #: Um objeto JSON. `None` é o evento sem conteúdo, recusado pela validação.
    payload: Mapping[str, Any] | None
    aggregate_type: str
    aggregate_id: str
    routing_key: str | None = None


def validate(event: IntegrationEvent) -> None:
    """Recusa o evento incompleto. Roda antes de qualquer conexão e nomeia o campo recusado."""
    if not event.destination or DESTINATION_PATTERN.fullmatch(event.destination) is None:
        raise InvalidIntegrationEvent("destination")
    for name in ("event_type", "aggregate_type", "aggregate_id"):
        if not getattr(event, name):
            raise InvalidIntegrationEvent(name)
    if event.event_version < 1:
        raise InvalidIntegrationEvent("event_version")
    if event.payload is None:
        raise InvalidIntegrationEvent("payload")

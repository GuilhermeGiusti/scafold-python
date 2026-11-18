"""Porta do gravador da outbox: gravar um evento de integração.

Ela exige estar dentro da transação que grava a mudança de estado: o use case abre
``unit_of_work.transaction("<nome>")`` e, dentro do bloco, chama ``writer.write(event)``. O commit
grava o estado e o evento juntos; um rollback não deixa nenhum dos dois.

Ela não conhece broker nenhum, e essa ausência é a garantia: o dual write é impossível por
construção, e não por disciplina.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from scafold.domain.outbox.value_objects.integration_event import IntegrationEvent


class IIntegrationWriter(Protocol):
    async def write(self, event: IntegrationEvent) -> UUID:
        """Grava a mensagem e devolve o id dela, a chave de idempotência do consumidor."""
        ...

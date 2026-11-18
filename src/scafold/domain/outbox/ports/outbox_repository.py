"""Porta das operações sobre a fila da outbox.

As escritas (reivindicar, marcar, reagendar, registrar falha) acontecem dentro da transação que a
drenagem abre pela Unit of Work, uma por mensagem. A porta não tem ``commit`` nem ``rollback``:
quem controla a transação é quem a abriu. A contagem do backlog é a única leitura, fora de
transação.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from scafold.domain.outbox.value_objects.backlog_entry import BacklogEntry
from scafold.domain.outbox.value_objects.failure import Failure
from scafold.domain.outbox.value_objects.pending_message import PendingMessage


class IOutboxRepository(Protocol):
    async def claim_next_pending(self, dispatcher: str) -> PendingMessage:
        """Reivindica a próxima pendente do carimbo, travando a linha.

        Levanta ``NoPendingMessage`` com a fila vazia. Fora de uma Unit of Work, é recusada: a
        trava só vale dentro da transação.
        """
        ...

    async def mark_published(self, message_id: UUID) -> None:
        """`PUBLISHED`, com `published_at` carimbado."""
        ...

    async def mark_dead(self, message_id: UUID) -> None:
        """`DEAD`, somando a tentativa que matou a mensagem."""
        ...

    async def schedule_retry(self, message_id: UUID, countdown_seconds: int) -> None:
        """Soma uma tentativa e empurra `available_at`."""
        ...

    async def record_failure(self, failure: Failure) -> None:
        """Uma linha em `outbox_error` para a tentativa que não deu certo."""
        ...

    async def backlog(self) -> list[BacklogEntry]:
        """As pendentes de TODOS os carimbos. Leitura, fora de transação.

        Sem filtro, de propósito: se cada processo publicasse só o próprio backlog, desligar o
        último processo de um broker faria a série sumir em vez de ir a zero.
        """
        ...

"""O repositório da fila da outbox sobre o código gerado pelo sqlc.

As escritas e a reivindicação pedem ``write_querier``: fora da transação ``outbox_drain``, a Unit of
Work recusa antes de qualquer consulta. O backlog é leitura e pede ``querier``, fora de transação.
As linhas geradas pelo sqlc nunca saem daqui: o repositório devolve ``PendingMessage`` e
``BacklogEntry``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from scafold.domain.outbox.errors.no_pending_message import NoPendingMessage
from scafold.domain.outbox.value_objects.backlog_entry import BacklogEntry
from scafold.domain.outbox.value_objects.failure import Failure
from scafold.domain.outbox.value_objects.pending_message import PendingMessage
from scafold.infrastructure.persistence.outbox.sqlc import outbox
from scafold.infrastructure.persistence.unit_of_work import UnitOfWork

#: O rótulo deste repositório em `db_query_duration_seconds`.
REPOSITORY_NAME = "outbox_repository"


class SqlOutboxRepository:
    """Implementa ``IOutboxRepository``. Recebe a ``UnitOfWork`` concreta."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def claim_next_pending(self, dispatcher: str) -> PendingMessage:
        async with self._unit_of_work.write_querier(REPOSITORY_NAME) as connection:
            row = await outbox.AsyncQuerier(connection).claim_next_pending(dispatcher=dispatcher)
        if row is None:
            raise NoPendingMessage()
        return PendingMessage(
            id=row.id,
            destination=row.destination,
            event_type=row.event_type,
            event_version=row.event_version,
            payload=_payload(row.payload),
            aggregate_type=row.aggregate_type,
            aggregate_id=row.aggregate_id,
            correlation_id=row.correlation_id,
            trace_context=row.trace_context,
            dispatcher=row.dispatcher,
            attempts=row.attempts,
            routing_key=row.routing_key,
        )

    async def mark_published(self, message_id: UUID) -> None:
        async with self._unit_of_work.write_querier(REPOSITORY_NAME) as connection:
            await outbox.AsyncQuerier(connection).mark_published(id=message_id)

    async def mark_dead(self, message_id: UUID) -> None:
        async with self._unit_of_work.write_querier(REPOSITORY_NAME) as connection:
            await outbox.AsyncQuerier(connection).mark_dead(id=message_id)

    async def schedule_retry(self, message_id: UUID, countdown_seconds: int) -> None:
        async with self._unit_of_work.write_querier(REPOSITORY_NAME) as connection:
            await outbox.AsyncQuerier(connection).schedule_retry(
                countdown_seconds=float(countdown_seconds), id=message_id
            )

    async def record_failure(self, failure: Failure) -> None:
        async with self._unit_of_work.write_querier(REPOSITORY_NAME) as connection:
            await outbox.AsyncQuerier(connection).insert_outbox_error(
                message_id=failure.message_id,
                attempt_no=failure.attempt_no,
                error_kind=failure.kind,
                error_detail=failure.detail,
            )

    async def backlog(self) -> list[BacklogEntry]:
        async with self._unit_of_work.querier(REPOSITORY_NAME) as connection:
            return [
                BacklogEntry(
                    dispatcher=row.dispatcher,
                    pending=row.pending,
                    oldest_age_seconds=row.oldest_age_seconds,
                )
                async for row in outbox.AsyncQuerier(connection).count_pending_by_dispatcher()
            ]


def _payload(value: Any) -> Mapping[str, Any]:
    """O ``jsonb`` chega como objeto ou como texto, conforme o codec do driver."""
    if isinstance(value, str):
        loaded: Mapping[str, Any] = json.loads(value)
        return loaded
    payload: Mapping[str, Any] = value
    return payload

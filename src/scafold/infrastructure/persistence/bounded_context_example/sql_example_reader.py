"""O leitor SQL de Example. Implementa ``IExampleReader``.

Lê sem abrir transação, pelo ``querier`` da Unit of Work: as queries saem com
``transaction="none"`` na métrica, ou com o nome da transação, se o leitor for chamado dentro de uma.
"""

from __future__ import annotations

from scafold.applications.queries.example_summary import ExampleSummary
from scafold.infrastructure.persistence.bounded_context_example.sqlc import example_read
from scafold.infrastructure.persistence.unit_of_work import UnitOfWork

#: O rótulo deste leitor em `db_query_duration_seconds`.
READER_NAME = "example_reader"


class SqlExampleReader:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._uow = unit_of_work

    async def list_summaries(self, *, limit: int) -> list[ExampleSummary]:
        async with self._uow.querier(READER_NAME) as connection:
            querier = example_read.AsyncQuerier(connection)
            return [
                ExampleSummary(
                    id=row.id,
                    label=row.label,
                    item_count=row.item_count,
                    archived=row.archived_at is not None,
                )
                async for row in querier.list_example_summaries(row_limit=limit)
            ]

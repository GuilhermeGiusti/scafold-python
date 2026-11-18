"""O repositório SQL do agregado Example. Implementa ``IExampleRepository``.

Ele NUNCA abre, commita ou reverte transação: pede a conexão à Unit of Work e grava na transação
que o use case abriu. Para escrever, pede ``write_querier``, que recusa fora da transação; para
ler, ``querier``, que funciona dentro ou fora dela. As linhas geradas pelo sqlc não saem daqui:
o ``ExampleRowMapper`` as traduz no agregado.
"""

from __future__ import annotations

from sqlalchemy import exc

from scafold.domain.bounded_context_example.aggregates.example import Example
from scafold.domain.bounded_context_example.errors.label_taken import LabelTaken
from scafold.domain.bounded_context_example.value_objects.example_id import ExampleId
from scafold.infrastructure.persistence.bounded_context_example.mappers.example_row_mapper import (
    ExampleRowMapper,
)
from scafold.infrastructure.persistence.bounded_context_example.sqlc import (
    example_read,
    example_write,
)
from scafold.infrastructure.persistence.unit_of_work import UnitOfWork

#: O rótulo deste repositório em `db_query_duration_seconds`: o nome da porta sem o `I`.
REPOSITORY_NAME = "example_repository"

#: A restrição da migration que vira `LabelTaken`. É o NOME que decide, e não a mensagem do
#: driver, que muda com a versão e o idioma do Postgres.
LABEL_UNIQUE_CONSTRAINT = "uq_example_label"


class SqlExampleRepository:
    def __init__(self, unit_of_work: UnitOfWork, mapper: ExampleRowMapper) -> None:
        self._uow = unit_of_work
        self._mapper = mapper

    async def add(self, example: Example) -> None:
        row = self._mapper.to_row(example)
        async with self._uow.write_querier(REPOSITORY_NAME) as connection:
            querier = example_write.AsyncQuerier(connection)
            try:
                await querier.insert_example(
                    example_write.InsertExampleParams(
                        id=row.id,
                        label=row.label,
                        category_code=row.category_code,
                        created_at=row.created_at,
                        archived_at=row.archived_at,
                    )
                )
            except exc.IntegrityError as failure:
                if _violated_constraint(failure) == LABEL_UNIQUE_CONSTRAINT:
                    raise LabelTaken("o nome ja pertence a outro example") from None
                raise
            # A raiz e os itens vão para duas tabelas na mesma transação: se um item falhar, a
            # raiz é revertida junto.
            for item in self._mapper.to_item_rows(example):
                await querier.insert_example_item(
                    id=item.id, example_id=item.example_id, name=item.name, position=item.position
                )

    async def get(self, example_id: ExampleId) -> Example | None:
        async with self._uow.querier(REPOSITORY_NAME) as connection:
            querier = example_read.AsyncQuerier(connection)
            row = await querier.get_example(id=example_id)
            if row is None:
                return None
            # O `:many` é um iterador: é consumido dentro do bloco, antes de a conexão voltar ao
            # pool.
            items = [item async for item in querier.list_example_items(example_id=example_id)]
        return self._mapper.to_aggregate(row, items)

    async def save(self, example: Example) -> None:
        async with self._uow.write_querier(REPOSITORY_NAME) as connection:
            await example_write.AsyncQuerier(connection).update_example_archived_at(
                archived_at=example.archived_at, id=example.id
            )

    async def remove_archived(self) -> int:
        async with self._uow.write_querier(REPOSITORY_NAME) as connection:
            return await example_write.AsyncQuerier(connection).delete_archived_examples()


def _violated_constraint(failure: exc.IntegrityError) -> str | None:
    """O nome da restrição violada, tirado da exceção do asyncpg que o SQLAlchemy embrulhou."""
    for candidate in (failure.orig, getattr(failure.orig, "__cause__", None)):
        name = getattr(candidate, "constraint_name", None)
        if isinstance(name, str):
            return name
    return None

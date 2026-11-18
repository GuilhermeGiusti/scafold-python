"""Contrato de métricas da camada de dados: transações e queries (ADR-005)."""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

#: `committed`: o bloco terminou e o COMMIT passou.
#: `rolled_back`: o bloco levantou (ou a conexão nem abriu) e a transação foi revertida.
#: `commit_failed`: o bloco terminou, mas o COMMIT falhou no banco.
type TransactionStatus = Literal["committed", "rolled_back", "commit_failed"]

type QueryStatus = Literal["ok", "error"]

#: O `error_type` de uma transação que commitou.
NO_ERROR = "none"

#: O `transaction` de uma query que rodou fora de qualquer Unit of Work.
NO_TRANSACTION = "none"


@runtime_checkable
class IPersistenceMetrics(Protocol):
    """Porta de métricas consumida pela ``UnitOfWork`` e pelo ouvinte de queries.

    Fica em ``infrastructure/persistence/`` porque só a infraestrutura a consome. Todos os rótulos
    são nomes fixos (transação, repositório, query), status e nome de classe de exceção. Id,
    parâmetro de query e mensagem de erro não vão para sinal algum.
    """

    def transaction_started(self, *, transaction: str) -> None:
        """Uma transação externa abriu. Métrica `db_transactions_in_flight` (+1)."""
        ...

    def transaction_finished(
        self,
        *,
        transaction: str,
        status: TransactionStatus,
        error_type: str,
        duration_seconds: float,
    ) -> None:
        """Métricas `db_transactions_in_flight` (-1), `db_transactions_total` e
        `db_transaction_duration_seconds`."""
        ...

    def query_executed(
        self,
        *,
        repository: str,
        query: str,
        transaction: str,
        status: QueryStatus,
        duration_seconds: float,
    ) -> None:
        """Uma query gerada pelo sqlc rodou. Métrica `db_query_duration_seconds`."""
        ...

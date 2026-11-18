"""Métricas da camada de dados escritas no log."""

from __future__ import annotations

import logging

from scafold.infrastructure.persistence.metrics.persistence_metrics import (
    QueryStatus,
    TransactionStatus,
)


class LoggingPersistenceMetrics:
    """Implementa ``IPersistenceMetrics`` escrevendo cada medição no log, em DEBUG, no formato que
    o Prometheus exporia. Trocar pelo adaptador OpenTelemetry não muda UoW, repositório nem use
    case."""

    def __init__(self, logger: logging.Logger) -> None:
        self._log = logger

    def transaction_started(self, *, transaction: str) -> None:
        self._log.debug("db_transactions_in_flight{transaction=%s} +1", transaction)

    def transaction_finished(
        self,
        *,
        transaction: str,
        status: TransactionStatus,
        error_type: str,
        duration_seconds: float,
    ) -> None:
        self._log.debug("db_transactions_in_flight{transaction=%s} -1", transaction)
        self._log.debug(
            "db_transactions_total{transaction=%s,status=%s,error_type=%s} +1",
            transaction,
            status,
            error_type,
        )
        self._log.debug(
            "db_transaction_duration_seconds{transaction=%s,status=%s} %.6f",
            transaction,
            status,
            duration_seconds,
        )

    def query_executed(
        self,
        *,
        repository: str,
        query: str,
        transaction: str,
        status: QueryStatus,
        duration_seconds: float,
    ) -> None:
        self._log.debug(
            "db_query_duration_seconds{repository=%s,query=%s,transaction=%s,status=%s} %.6f",
            repository,
            query,
            transaction,
            status,
            duration_seconds,
        )

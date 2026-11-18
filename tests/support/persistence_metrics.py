"""Dublê de ``IPersistenceMetrics``: guarda cada medição da camada de dados."""

from __future__ import annotations

from dataclasses import dataclass, field

from scafold.infrastructure.persistence.metrics.persistence_metrics import (
    QueryStatus,
    TransactionStatus,
)


@dataclass
class RecordingPersistenceMetrics:
    started: list[str] = field(default_factory=list)
    finished: list[tuple[str, TransactionStatus, str]] = field(default_factory=list)
    queries: list[tuple[str, str, str, QueryStatus]] = field(default_factory=list)

    def transaction_started(self, *, transaction: str) -> None:
        self.started.append(transaction)

    def transaction_finished(
        self,
        *,
        transaction: str,
        status: TransactionStatus,
        error_type: str,
        duration_seconds: float,
    ) -> None:
        self.finished.append((transaction, status, error_type))

    def query_executed(
        self,
        *,
        repository: str,
        query: str,
        transaction: str,
        status: QueryStatus,
        duration_seconds: float,
    ) -> None:
        self.queries.append((repository, query, transaction, status))

"""Métricas da camada de dados com OpenTelemetry."""

from __future__ import annotations

from opentelemetry.metrics import Counter, Histogram, MeterProvider, UpDownCounter

from scafold.infrastructure.persistence.metrics.persistence_metrics import (
    QueryStatus,
    TransactionStatus,
)

#: O escopo de instrumentação: o "dono" das métricas e dos spans da camada de dados.
INSTRUMENTATION_SCOPE = "scafold.persistence"

#: Limites dos histogramas, em segundos. O padrão do SDK (0, 5, 10... 10000) foi pensado para
#: milissegundos: em segundos, toda transação cairia no primeiro bucket.
DURATION_BUCKETS_SECONDS = (
    0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0,
)


class OpenTelemetryPersistenceMetrics:
    """Implementa ``IPersistenceMetrics`` com instrumentos OpenTelemetry.

    O Prometheus publica ``db_transactions_total``, ``db_transaction_duration_seconds``,
    ``db_transactions_in_flight`` e ``db_query_duration_seconds``, os nomes da porta.
    """

    def __init__(self, meter_provider: MeterProvider) -> None:
        meter = meter_provider.get_meter(INSTRUMENTATION_SCOPE)
        self._in_flight: UpDownCounter = meter.create_up_down_counter(
            "db.transactions.in_flight", unit="{transaction}", description="Transacoes abertas"
        )
        self._transactions: Counter = meter.create_counter(
            "db.transactions", unit="{transaction}", description="Transacoes encerradas"
        )
        self._transaction_duration: Histogram = meter.create_histogram(
            "db.transaction.duration",
            unit="s",
            description="Duracao da transacao, da conexao ao COMMIT ou ROLLBACK",
            explicit_bucket_boundaries_advisory=DURATION_BUCKETS_SECONDS,
        )
        self._query_duration: Histogram = meter.create_histogram(
            "db.query.duration",
            unit="s",
            description="Duracao de cada query gerada pelo sqlc",
            explicit_bucket_boundaries_advisory=DURATION_BUCKETS_SECONDS,
        )

    def transaction_started(self, *, transaction: str) -> None:
        self._in_flight.add(1, {"transaction": transaction})

    def transaction_finished(
        self,
        *,
        transaction: str,
        status: TransactionStatus,
        error_type: str,
        duration_seconds: float,
    ) -> None:
        self._in_flight.add(-1, {"transaction": transaction})
        self._transactions.add(
            1, {"transaction": transaction, "status": status, "error_type": error_type}
        )
        self._transaction_duration.record(
            duration_seconds, {"transaction": transaction, "status": status}
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
        self._query_duration.record(
            duration_seconds,
            {"repository": repository, "query": query, "transaction": transaction, "status": status},
        )

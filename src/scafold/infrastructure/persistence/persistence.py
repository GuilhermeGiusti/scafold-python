"""A montagem da camada de dados: engine, ouvinte de queries e Unit of Work."""

from __future__ import annotations

from dataclasses import dataclass

from opentelemetry.trace import TracerProvider
from sqlalchemy.ext.asyncio import AsyncEngine

from scafold.infrastructure.persistence.engine import open_engine
from scafold.infrastructure.persistence.metrics.persistence_metrics import IPersistenceMetrics
from scafold.infrastructure.persistence.query_metrics import instrument_queries
from scafold.infrastructure.persistence.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class Persistence:
    engine: AsyncEngine
    unit_of_work: UnitOfWork

    async def close(self) -> None:
        """Devolve as conexões do pool. No encerramento, no mesmo event loop que as abriu."""
        await self.engine.dispose()


def open_persistence(
    database_url: str,
    metrics: IPersistenceMetrics,
    tracer_provider: TracerProvider | None = None,
) -> Persistence:
    """Uma vez por processo. A mesma ``metrics`` mede transações e queries, e o mesmo
    ``tracer_provider`` abre o span da transação e o de cada query."""
    engine = open_engine(database_url)
    instrument_queries(engine, metrics, tracer_provider=tracer_provider)
    unit_of_work = UnitOfWork(engine=engine, metrics=metrics, tracer_provider=tracer_provider)
    return Persistence(engine=engine, unit_of_work=unit_of_work)

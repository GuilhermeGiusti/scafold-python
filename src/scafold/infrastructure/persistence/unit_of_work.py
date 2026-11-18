"""A Unit of Work: uma transação com nome, propagada por ``contextvars`` e medida (ADR-004).

O use case de escrita abre a transação; tudo o que roda dentro dela participa sem receber nada por
parâmetro. Repositórios e leitores nunca abrem, commitam ou revertem: pedem a conexão por
``write_querier(nome)`` para escrever (que recusa fora da transação) ou ``querier(nome)`` para ler.

**A transação vive numa ``ContextVar``, nunca num atributo.** A ``UnitOfWork`` é uma só para o
processo. Num atributo, duas requisições concorrentes do mesmo event loop dividiriam a transação.

**Chamada aninhada participa.** Usa a conexão da externa, e quem commita é a externa. Não há
``SAVEPOINT``, de propósito: um erro no trecho aninhado reverte a transação inteira.

**Só a transação externa é medida e abre span** (``db.transaction <nome>``). O span fica corrente
enquanto o bloco roda, então os spans das queries nascem como filhos dele.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from contextvars import ContextVar

from opentelemetry.trace import TracerProvider
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from scafold.infrastructure.persistence.metrics.persistence_metrics import (
    NO_ERROR,
    NO_TRANSACTION,
    IPersistenceMetrics,
    TransactionStatus,
)
from scafold.infrastructure.persistence.persistence_spans import (
    mark_failed,
    persistence_tracer,
    transaction_span_name,
)

#: A conexão da transação ativa no fluxo corrente.
_connection: ContextVar[AsyncConnection | None] = ContextVar("uow_connection", default=None)

#: O nome da transação externa ativa, para rotular as queries que rodam dentro dela.
_transaction_name: ContextVar[str] = ContextVar("uow_transaction_name", default=NO_TRANSACTION)

#: O repositório que pediu a conexão, para rotular as queries que ele executa.
_repository: ContextVar[str | None] = ContextVar("uow_repository", default=None)


class OutsideUnitOfWork(RuntimeError):
    """Escrita que exige transação acontecendo fora de qualquer Unit of Work."""


def in_transaction() -> bool:
    """Há uma Unit of Work aberta no fluxo corrente?"""
    return _connection.get() is not None


def current_transaction() -> str:
    """O nome da transação externa ativa, ou ``"none"`` fora de qualquer Unit of Work."""
    return _transaction_name.get()


def current_repository() -> str | None:
    """O repositório que pediu a conexão em uso, ou ``None``."""
    return _repository.get()


class UnitOfWork:
    """Implementa ``IUnitOfWork``. Construída uma vez na montagem do processo."""

    def __init__(
        self,
        *,
        engine: AsyncEngine,
        metrics: IPersistenceMetrics,
        clock: Callable[[], float] = time.perf_counter,
        tracer_provider: TracerProvider | None = None,
    ) -> None:
        self._engine = engine
        self._metrics = metrics
        self._clock = clock
        self._tracer = persistence_tracer(tracer_provider)

    def transaction(self, name: str) -> AbstractAsyncContextManager[None]:
        """Abre a transação ``name``, ou participa da que já está aberta."""
        return self._open(name)

    @asynccontextmanager
    async def write_querier(self, repository: str) -> AsyncIterator[AsyncConnection]:
        """A conexão da transação ativa, para ESCREVER. Sem transação, recusa.

        Sem esta recusa, uma escrita esquecida fora da Unit of Work iria para uma conexão do pool,
        que o SQLAlchemy reverte na devolução: a gravação se perderia sem erro nenhum.
        """
        if _connection.get() is None:
            raise OutsideUnitOfWork(f"{repository} pediu conexao de escrita fora de uma Unit of Work")
        async with self.querier(repository) as connection:
            yield connection

    @asynccontextmanager
    async def querier(self, repository: str) -> AsyncIterator[AsyncConnection]:
        """A conexão da transação ativa, se houver; senão, uma conexão do pool. Para LER.

        ``repository`` é o nome fixo de quem pede, em snake_case. Ele rotula cada query executada
        com esta conexão em ``db_query_duration_seconds``.
        """
        token = _repository.set(repository)
        try:
            active = _connection.get()
            if active is not None:
                # NÃO fecha: quem abriu a transação é quem a encerra.
                yield active
                return
            async with self._engine.connect() as connection:
                yield connection
        finally:
            _repository.reset(token)

    @asynccontextmanager
    async def _open(self, name: str) -> AsyncIterator[None]:
        if _connection.get() is not None:
            # Aninhada: participa. Quem commita, reverte e mede é a externa.
            yield
            return

        started = self._clock()
        self._metrics.transaction_started(transaction=name)
        status: TransactionStatus = "committed"
        error_type = NO_ERROR
        body_finished = False
        # O span abre antes de pedir a conexão, como a medição: a espera pelo pool conta.
        with self._tracer.start_as_current_span(
            transaction_span_name(name),
            attributes={"transaction": name},
            record_exception=False,
            set_status_on_exception=False,
        ) as span:
            try:
                async with self._engine.connect() as connection:
                    connection_token = _connection.set(connection)
                    name_token = _transaction_name.set(name)
                    try:
                        async with connection.begin():
                            yield
                            # Só chega aqui se o bloco terminou sem erro. Uma falha depois disto,
                            # na saída do `begin()`, é do COMMIT.
                            body_finished = True
                    finally:
                        _transaction_name.reset(name_token)
                        _connection.reset(connection_token)
            except BaseException as failure:
                # BaseException: cancelamento também reverte a transação e precisa ser contado.
                status = "commit_failed" if body_finished else "rolled_back"
                error_type = type(failure).__name__
                raise
            finally:
                span.set_attribute("status", status)
                span.set_attribute("error_type", error_type)
                if status != "committed":
                    mark_failed(span, error_type)
                self._metrics.transaction_finished(
                    transaction=name,
                    status=status,
                    error_type=error_type,
                    duration_seconds=self._clock() - started,
                )

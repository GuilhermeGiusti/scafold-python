"""A drenagem da outbox: um ciclo do job, chamado a cada disparo do agendamento.

``OutboxDrainUseCase`` segue o contrato ``AsyncNullaryUseCase[DrainResult]``. É invocável sem o
agendador; trocar o agendador nunca muda a lógica de drenagem.

**Uma transação por mensagem, aberta pela Unit of Work** (ADR-006): cada mensagem roda dentro de
``transaction("outbox_drain")``, que reivindica, envia, marca e fecha. Segurar a transação durante
o lote deixaria a trava aberta durante centenas de chamadas de rede.

**A fila vazia também custa uma transação.** Reivindicar trava a linha e exige a transação aberta.
``NoPendingMessage`` é tratado dentro do bloco: a transação commita vazia.

**A drenagem decide o destino da mensagem; o publicador só relata.** Contar tentativas, escolher
entre reagendar e matar e escrever no banco é daqui.

**O núcleo não conhece a telemetria.** As medições passam pela porta ``IOutboxMetrics``; o span de
envio é aberto por um envoltório do publicador, na infraestrutura (emenda da ADR-006).
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from typing import Literal, assert_never

from scafold.applications.commands.drain_result import DrainResult
from scafold.applications.ports.outbox_metrics import (
    REASON_ATTEMPTS_EXHAUSTED,
    REASON_PERMANENT,
    RESULT_PERMANENT,
    RESULT_PUBLISHED,
    RESULT_TRANSIENT,
    DispatchResult,
    IOutboxMetrics,
)
from scafold.applications.shared.use_case import AsyncNullaryUseCase
from scafold.domain.outbox.dispatchers import MAX_ATTEMPTS
from scafold.domain.outbox.errors.no_pending_message import NoPendingMessage
from scafold.domain.outbox.ports.dispatcher import IDispatcher
from scafold.domain.outbox.ports.outbox_repository import IOutboxRepository
from scafold.domain.outbox.value_objects.dispatch_outcome import DispatchOutcome
from scafold.domain.outbox.value_objects.failure import (
    FAILURE_PERMANENT,
    FAILURE_TRANSIENT,
    Failure,
)
from scafold.domain.outbox.value_objects.pending_message import PendingMessage
from scafold.domain.outbox.value_objects.permanent_failure import PermanentFailure
from scafold.domain.outbox.value_objects.published import Published
from scafold.domain.outbox.value_objects.transient_failure import TransientFailure
from scafold.domain.shared.persistence.unit_of_work import IUnitOfWork

#: O nome da transação de cada mensagem nas métricas da camada de dados.
TRANSACTION_NAME = "outbox_drain"

#: O começo do resumo de cada ciclo, em DEBUG: ciclo sem trabalho é estado normal.
CYCLE_SUMMARY = "outbox: ciclo de drenagem concluido"

type _Applied = Literal["published", "retried", "dead"]


class OutboxDrainUseCase(AsyncNullaryUseCase[DrainResult]):
    """Drena a fila de um carimbo, uma mensagem por transação da Unit of Work."""

    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        repository: IOutboxRepository,
        dispatcher: IDispatcher,
        metrics: IOutboxMetrics,
        batch_size: int,
        retry_countdown_seconds: int,
        stop_requested: Callable[[], bool],
        known_dispatchers: Sequence[str],
        logger: logging.Logger,
        clock: Callable[[], float],
    ) -> None:
        self._unit_of_work = unit_of_work
        self._repository = repository
        self._dispatcher = dispatcher
        self._metrics = metrics
        self._batch_size = batch_size
        self._retry_countdown_seconds = retry_countdown_seconds
        self._stop_requested = stop_requested
        self._known_dispatchers = known_dispatchers
        self._logger = logger
        self._clock = clock

    async def execute(self) -> DrainResult:
        """Drena até ``batch_size`` mensagens, uma transação cada. Nunca sem limite.

        A parada é conferida antes de cada reivindicação: o sinal termina a mensagem em
        andamento, e não o lote inteiro.
        """
        started = self._clock()
        counts: dict[_Applied, int] = {"published": 0, "retried": 0, "dead": 0}
        for _ in range(self._batch_size):
            if self._stop_requested():
                break
            applied = await self._process_one()
            if applied is None:
                break
            counts[applied] += 1
        await self._record_backlog()
        seconds = self._clock() - started
        self._metrics.record_drain_duration(seconds)
        self._logger.debug(
            "%s publicadas=%d reagendadas=%d mortas=%d duracao=%.3f",
            CYCLE_SUMMARY,
            counts["published"],
            counts["retried"],
            counts["dead"],
            seconds,
        )
        return DrainResult(
            published=counts["published"],
            retried=counts["retried"],
            dead=counts["dead"],
            seconds=seconds,
        )

    async def _process_one(self) -> _Applied | None:
        """Uma mensagem, uma transação. ``None`` quando não havia trabalho."""
        async with self._unit_of_work.transaction(TRANSACTION_NAME):
            try:
                claimed = await self._repository.claim_next_pending(self._dispatcher.name)
            except NoPendingMessage:
                # Fila vazia é estado normal: o bloco termina sem erro, e a transação commita.
                return None
            outcome = await self._dispatcher.dispatch(claimed)
            return await self._apply(claimed, outcome)

    async def _apply(self, claimed: PendingMessage, outcome: DispatchOutcome) -> _Applied:
        attempt_no = claimed.attempts + 1
        match outcome:
            case Published():
                await self._repository.mark_published(claimed.id)
                self._attempt(claimed, RESULT_PUBLISHED)
                return "published"
            case PermanentFailure(detail):
                await self._repository.mark_dead(claimed.id)
                await self._failure(claimed, attempt_no, FAILURE_PERMANENT, detail)
                self._attempt(claimed, RESULT_PERMANENT)
                self._metrics.record_dead(
                    event=claimed.event_type,
                    destination=claimed.destination,
                    reason=REASON_PERMANENT,
                )
                return "dead"
            case TransientFailure(detail):
                await self._failure(claimed, attempt_no, FAILURE_TRANSIENT, detail)
                self._attempt(claimed, RESULT_TRANSIENT)
                if attempt_no >= MAX_ATTEMPTS:
                    # A quinta falha transitória já foi contada como tentativa. Sem a contagem de
                    # mortas, nada sinalizaria que a mensagem morreu.
                    await self._repository.mark_dead(claimed.id)
                    self._metrics.record_dead(
                        event=claimed.event_type,
                        destination=claimed.destination,
                        reason=REASON_ATTEMPTS_EXHAUSTED,
                    )
                    return "dead"
                await self._repository.schedule_retry(claimed.id, self._retry_countdown_seconds)
                return "retried"
            case _:
                assert_never(outcome)

    async def _failure(
        self, claimed: PendingMessage, attempt_no: int, kind: str, detail: str
    ) -> None:
        # O detalhe vem do publicador e nunca repete o payload.
        await self._repository.record_failure(
            Failure(message_id=claimed.id, attempt_no=attempt_no, kind=kind, detail=detail)
        )

    def _attempt(self, claimed: PendingMessage, result: DispatchResult) -> None:
        self._metrics.record_attempt(
            event=claimed.event_type, destination=claimed.destination, result=result
        )

    async def _record_backlog(self) -> None:
        """O backlog de todos os carimbos, semeado com zero: a série vai a zero em vez de sumir."""
        backlog = {name: (0, 0.0) for name in self._known_dispatchers}
        for entry in await self._repository.backlog():
            backlog[entry.dispatcher] = (entry.pending, entry.oldest_age_seconds)
        self._metrics.record_backlog(backlog)

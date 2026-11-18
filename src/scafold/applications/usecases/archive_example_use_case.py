"""Use case de command sem retorno: arquivar um Example."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from scafold.applications.commands.archive_example_command import ArchiveExampleCommand
from scafold.applications.errors.example_not_found import ExampleNotFound
from scafold.applications.shared.use_case import AsyncUnitUseCase
from scafold.domain.bounded_context_example.repositories.example_repository import (
    IExampleRepository,
)
from scafold.domain.bounded_context_example.value_objects.example_id import ExampleId
from scafold.domain.shared.events.event_base import IDomainEventDispatcher
from scafold.domain.shared.persistence.unit_of_work import IUnitOfWork

TRANSACTION_NAME = "archive_example"


class ArchiveExampleUseCase(AsyncUnitUseCase[ArchiveExampleCommand]):
    """Carrega, pede a transição ao agregado e grava. O resultado é o novo estado, não um valor.

    A leitura fica dentro da transação porque precisa ver o estado consistente com a escrita do
    mesmo bloco. Falhas saem como exceção (``ExampleNotFound``, ``InvalidTransition``), nunca
    como ``False``.
    """

    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        repository: IExampleRepository,
        dispatcher: IDomainEventDispatcher,
        clock: Callable[[], datetime],
    ) -> None:
        self._unit_of_work = unit_of_work
        self._repository = repository
        self._dispatcher = dispatcher
        self._clock = clock

    async def execute(self, input: ArchiveExampleCommand) -> None:
        async with self._unit_of_work.transaction(TRANSACTION_NAME):
            example = await self._repository.get(ExampleId(input.example_id))
            if example is None:
                raise ExampleNotFound("example nao encontrado")
            example.archive(now=self._clock())
            await self._repository.save(example)
            events = self._dispatcher.collect(example)
        self._dispatcher.dispatch(events)

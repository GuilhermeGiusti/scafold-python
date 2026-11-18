"""Use case de command que devolve valor: criar um Example e devolver o id."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from scafold.applications.commands.create_example_command import CreateExampleCommand
from scafold.applications.ports.category_gateway import ICategoryGateway
from scafold.applications.shared.use_case import AsyncUseCase
from scafold.domain.bounded_context_example.aggregates.example import Example
from scafold.domain.bounded_context_example.repositories.example_repository import (
    IExampleRepository,
)
from scafold.domain.bounded_context_example.value_objects.example_id import ExampleId
from scafold.domain.outbox.ports.integration_writer import IIntegrationWriter
from scafold.domain.outbox.value_objects.integration_event import IntegrationEvent
from scafold.domain.shared.events.event_base import IDomainEventDispatcher
from scafold.domain.shared.persistence.unit_of_work import IUnitOfWork

#: O nome da transação nas métricas. Literal fixo, o nome do use case sem o sufixo.
TRANSACTION_NAME = "create_example"

#: O destino lógico do evento de integração. A Strategy o traduz para o alvo real no envio.
INTEGRATION_DESTINATION = "example"
INTEGRATION_EVENT_TYPE = "example.created"
INTEGRATION_EVENT_VERSION = 1


class CreateExampleUseCase(AsyncUseCase[CreateExampleCommand, ExampleId]):
    """Orquestra a criação. Decide a ordem; quem diz o que é válido é o agregado.

    1. Fora da transação: consulta o serviço externo, monta e valida o agregado. Cada instante
       dentro do bloco prende uma conexão do pool, e I/O externo nunca entra nele.
    2. Dentro da transação: grava o agregado, grava o evento de integração na outbox (o mesmo
       commit grava os dois, ou nenhum) e recolhe os eventos de domínio.
    3. Depois do commit: despacha os eventos de domínio aos handlers. Se o bloco levantar, o
       despacho nunca é alcançado.
    """

    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        repository: IExampleRepository,
        gateway: ICategoryGateway,
        writer: IIntegrationWriter,
        dispatcher: IDomainEventDispatcher,
        clock: Callable[[], datetime],
    ) -> None:
        self._unit_of_work = unit_of_work
        self._repository = repository
        self._gateway = gateway
        self._writer = writer
        self._dispatcher = dispatcher
        self._clock = clock

    async def execute(self, input: CreateExampleCommand) -> ExampleId:
        category = await self._gateway.classify(input.label)
        example = Example.create(label=input.label, category=category, now=self._clock())
        for name in input.item_names:
            example.add_item(name)

        async with self._unit_of_work.transaction(TRANSACTION_NAME):
            await self._repository.add(example)
            await self._writer.write(example_created_event(example))
            events = self._dispatcher.collect(example)

        self._dispatcher.dispatch(events)
        return example.id


def example_created_event(example: Example) -> IntegrationEvent:
    """O contrato do evento que sai do processo. Mudar o formato pede versão nova."""
    return IntegrationEvent(
        destination=INTEGRATION_DESTINATION,
        event_type=INTEGRATION_EVENT_TYPE,
        event_version=INTEGRATION_EVENT_VERSION,
        payload={
            "id": str(example.id),
            "label": example.label,
            "category": example.category.value,
            "item_count": len(example.items),
        },
        aggregate_type="example",
        aggregate_id=str(example.id),
    )

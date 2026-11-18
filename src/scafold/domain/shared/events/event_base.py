"""Contratos de eventos de domínio, dos seus handlers e do seu despacho."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from scafold.domain.shared.aggregates.aggregate_root import AggregateRoot


@runtime_checkable
class IDomainEvent(Protocol):
    """Fato passado e imutável do negócio, emitido pelo próprio agregado.

    Todo evento implementa este contrato estendendo ``DomainEvent``, a base concreta que fornece
    ``occurred_on`` e fixa ``eq=False`` (os eventos vivem num ``set`` e precisam ser hashable).

    O despacho interno é por classe (``listener_to`` + ``isinstance``); ``name()`` e
    ``versioning()`` servem para serialização e para o rótulo ``event_name`` das métricas.
    """

    occurred_on: float
    """Instante em epoch UTC."""

    def versioning(self) -> str:
        """Versão do formato do evento, começando em ``"1"``."""
        ...

    def name(self) -> str:
        """Nome estável no formato ``<contexto>.<agregado>.<fato>``. Renomear quebra a série."""
        ...

    def to_json(self) -> dict[str, Any]:
        """Representação serializável do evento: ``versioning``, ``name``, campos e instante."""
        ...


@runtime_checkable
class IDomainEventHandler(Protocol):
    """Handler de evento de domínio: roda depois do commit da Unit of Work.

    Registrado no ``DomainEventManager`` (``infrastructure/events/``) e disparado pelo
    ``dispatch`` da porta ``IDomainEventDispatcher``. Não trata as próprias falhas: o manager
    captura a exceção, registra no log e na métrica (``status="error"``) e segue para o próximo
    handler. Engolir a falha dentro do handler esconderia o erro da métrica.
    """

    def listener_to(self) -> list[type[IDomainEvent]]:
        """Classes de evento que este handler escuta. Lido uma vez, no registro."""
        ...

    def handle(self, event: IDomainEvent) -> None:
        """Trata o evento."""
        ...


@runtime_checkable
class IDomainEventDispatcher(Protocol):
    """Porta de despacho dos eventos de domínio, consumida pelos use cases.

    O domínio define o contrato e a implementação chega de fora: ``DomainEventDispatcher``, sobre
    ``blinker``, em ``infrastructure/events/``. Nos testes de use case basta um dublê em memória.

    Uso canônico num use case::

        async with unit_of_work.transaction("create_example"):
            await repository.add(aggregate)
            events = dispatcher.collect(aggregate)   # dentro da Unit of Work
        dispatcher.dispatch(events)                  # depois do commit
    """

    def collect[IdT](self, aggregate: AggregateRoot[IdT]) -> set[IDomainEvent]:
        """Copia os eventos não comitados do agregado e limpa o agregado."""
        ...

    def dispatch(self, events: Iterable[IDomainEvent]) -> None:
        """Entrega cada evento aos handlers. Chame depois do commit."""
        ...

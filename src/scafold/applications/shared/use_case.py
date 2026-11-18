"""Os contratos de use case: o formato de ``execute`` que todo use case segue (ADR-008).

São ``Protocol``. Os use cases herdam deles explicitamente, para que o mypy confira a assinatura na
própria definição da classe, e não só no ponto em que alguém a usa.

| Protocolo            | Recebe   | Devolve | Uso típico                              |
|----------------------|----------|---------|-----------------------------------------|
| ``UseCase[I, O]``      | um input | um ``O``  | command que devolve o id criado; query  |
| ``UnitUseCase[I]``     | um input | nada    | command que só altera estado            |
| ``NullaryUseCase[O]``  | nada     | um ``O``  | query sem filtro; ciclo de um job       |
| ``ExecuterUseCase``    | nada     | nada    | job disparado por agendador             |

Cada um tem a versão ``Async*``, para use cases que esperam I/O.

O que não fazer:

- decidir comportamento com ``isinstance`` contra os contratos: em runtime eles só conferem se
  existe um ``execute``, e o contrato parametrizado levanta ``TypeError``;
- receber argumentos soltos em ``execute``: o contrato exige um único input;
- escrever código genérico que aceite use case síncrono e assíncrono pelo mesmo contrato.
"""

from typing import Protocol, runtime_checkable

# ---------- Sync ----------


@runtime_checkable
class NullaryUseCase[O](Protocol):
    def execute(self) -> O: ...


@runtime_checkable
class UnitUseCase[I](Protocol):
    def execute(self, input: I) -> None: ...


@runtime_checkable
class UseCase[I, O](Protocol):
    def execute(self, input: I) -> O: ...


@runtime_checkable
class ExecuterUseCase(Protocol):
    def execute(self) -> None: ...


# ---------- Async ----------


@runtime_checkable
class AsyncNullaryUseCase[O](Protocol):
    async def execute(self) -> O: ...


@runtime_checkable
class AsyncUnitUseCase[I](Protocol):
    async def execute(self, input: I) -> None: ...


@runtime_checkable
class AsyncUseCase[I, O](Protocol):
    async def execute(self, input: I) -> O: ...


@runtime_checkable
class AsyncExecuterUseCase(Protocol):
    async def execute(self) -> None: ...

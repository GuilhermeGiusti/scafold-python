"""Os quatro decorators assíncronos, um por contrato ``Async*``.

Mesma regra dos síncronos: herdam o contrato que envolvem e recebem o rótulo ``use_case`` como
literal fixo. O ``await`` fica dentro do bloco observado, então a duração medida é a da execução
inteira, e não só a da criação da corrotina.
"""

from __future__ import annotations

from scafold.applications.shared.use_case import (
    AsyncExecuterUseCase,
    AsyncNullaryUseCase,
    AsyncUnitUseCase,
    AsyncUseCase,
)
from scafold.infrastructure.observability.use_case_observer import UseCaseObserver


class AsyncObservedUseCase[I, O](AsyncUseCase[I, O]):
    def __init__(
        self, inner: AsyncUseCase[I, O], *, use_case: str, observer: UseCaseObserver
    ) -> None:
        self._inner = inner
        self._use_case = use_case
        self._observer = observer

    async def execute(self, input: I) -> O:
        with self._observer.observe(self._use_case):
            return await self._inner.execute(input)


class AsyncObservedUnitUseCase[I](AsyncUnitUseCase[I]):
    def __init__(
        self, inner: AsyncUnitUseCase[I], *, use_case: str, observer: UseCaseObserver
    ) -> None:
        self._inner = inner
        self._use_case = use_case
        self._observer = observer

    async def execute(self, input: I) -> None:
        with self._observer.observe(self._use_case):
            await self._inner.execute(input)


class AsyncObservedNullaryUseCase[O](AsyncNullaryUseCase[O]):
    def __init__(
        self, inner: AsyncNullaryUseCase[O], *, use_case: str, observer: UseCaseObserver
    ) -> None:
        self._inner = inner
        self._use_case = use_case
        self._observer = observer

    async def execute(self) -> O:
        with self._observer.observe(self._use_case):
            return await self._inner.execute()


class AsyncObservedExecuterUseCase(AsyncExecuterUseCase):
    def __init__(
        self, inner: AsyncExecuterUseCase, *, use_case: str, observer: UseCaseObserver
    ) -> None:
        self._inner = inner
        self._use_case = use_case
        self._observer = observer

    async def execute(self) -> None:
        with self._observer.observe(self._use_case):
            await self._inner.execute()

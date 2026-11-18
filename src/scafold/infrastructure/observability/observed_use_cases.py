"""Os quatro decorators síncronos, um por contrato.

Cada decorator herda o contrato que envolve, então o mypy confere que ele é substituível pelo use
case cru. O rótulo ``use_case`` é um literal fixo em snake_case, o nome do use case sem o sufixo
(``CreateExampleUseCase`` vira ``"create_example"``): renomear a classe não quebra a série.
"""

from __future__ import annotations

from scafold.applications.shared.use_case import (
    ExecuterUseCase,
    NullaryUseCase,
    UnitUseCase,
    UseCase,
)
from scafold.infrastructure.observability.use_case_observer import UseCaseObserver


class ObservedUseCase[I, O](UseCase[I, O]):
    def __init__(self, inner: UseCase[I, O], *, use_case: str, observer: UseCaseObserver) -> None:
        self._inner = inner
        self._use_case = use_case
        self._observer = observer

    def execute(self, input: I) -> O:
        with self._observer.observe(self._use_case):
            return self._inner.execute(input)


class ObservedUnitUseCase[I](UnitUseCase[I]):
    def __init__(
        self, inner: UnitUseCase[I], *, use_case: str, observer: UseCaseObserver
    ) -> None:
        self._inner = inner
        self._use_case = use_case
        self._observer = observer

    def execute(self, input: I) -> None:
        with self._observer.observe(self._use_case):
            self._inner.execute(input)


class ObservedNullaryUseCase[O](NullaryUseCase[O]):
    def __init__(
        self, inner: NullaryUseCase[O], *, use_case: str, observer: UseCaseObserver
    ) -> None:
        self._inner = inner
        self._use_case = use_case
        self._observer = observer

    def execute(self) -> O:
        with self._observer.observe(self._use_case):
            return self._inner.execute()


class ObservedExecuterUseCase(ExecuterUseCase):
    def __init__(
        self, inner: ExecuterUseCase, *, use_case: str, observer: UseCaseObserver
    ) -> None:
        self._inner = inner
        self._use_case = use_case
        self._observer = observer

    def execute(self) -> None:
        with self._observer.observe(self._use_case):
            self._inner.execute()

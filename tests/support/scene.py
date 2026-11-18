"""A cena dos testes: os use cases do processo montados sobre os fakes.

Usa o mesmo ``build_use_cases`` da produção, com os decorators de observabilidade, e só troca as
portas. Assim os testes de aplicação, da API, da CLI e da tela exercitam a montagem real.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from opentelemetry.trace import TracerProvider

from scafold.bootstrap.composition import LOGGER_NAME, UseCases, build_use_cases
from scafold.infrastructure.observability.use_case_observer import UseCaseObserver

from .fakes import (
    FakeUnitOfWork,
    InMemoryExampleReader,
    InMemoryExampleRepository,
    InMemoryIntegrationWriter,
    InMemoryStore,
    KeywordCategoryGateway,
    RecordingDomainEventDispatcher,
    RecordingUseCaseMetrics,
)

#: O instante fixo do relógio dos use cases.
NOW = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)


@dataclass
class Scene:
    store: InMemoryStore
    unit_of_work: FakeUnitOfWork
    repository: InMemoryExampleRepository
    dispatcher: RecordingDomainEventDispatcher
    use_case_metrics: RecordingUseCaseMetrics
    use_cases: UseCases


def build_scene(
    *, now: datetime = NOW, tracer_provider: TracerProvider | None = None
) -> Scene:
    store = InMemoryStore()
    unit_of_work = FakeUnitOfWork(store)
    repository = InMemoryExampleRepository(unit_of_work)
    dispatcher = RecordingDomainEventDispatcher()
    metrics = RecordingUseCaseMetrics()
    observer = UseCaseObserver(
        metrics=metrics, logger=logging.getLogger(LOGGER_NAME), tracer_provider=tracer_provider
    )
    use_cases = build_use_cases(
        unit_of_work=unit_of_work,
        repository=repository,
        reader=InMemoryExampleReader(store),
        gateway=KeywordCategoryGateway(),
        writer=InMemoryIntegrationWriter(unit_of_work),
        dispatcher=dispatcher,
        clock=lambda: now,
        observer=observer,
    )
    return Scene(
        store=store,
        unit_of_work=unit_of_work,
        repository=repository,
        dispatcher=dispatcher,
        use_case_metrics=metrics,
        use_cases=use_cases,
    )

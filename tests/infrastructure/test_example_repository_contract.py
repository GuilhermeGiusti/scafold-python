from uuid import uuid4

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from scafold.domain.bounded_context_example.aggregates.example import Example
from scafold.domain.bounded_context_example.errors.label_taken import LabelTaken
from scafold.domain.bounded_context_example.value_objects.category import Category
from scafold.domain.bounded_context_example.value_objects.example_id import ExampleId
from scafold.infrastructure.persistence.unit_of_work import OutsideUnitOfWork

from ..conftest import Backend, Run
from ..support.scene import NOW

scenarios("infrastructure/example_repository_contract.feature")

# Obrigatório: os testes gerados por `scenarios` só pedem fixtures quando um step as pede, e a
# fixture parametrizada precisa estar declarada no teste para gerar um teste por parâmetro.
pytestmark = pytest.mark.usefixtures("backend")


class Boom(Exception):
    """Uma falha depois da gravação, dentro da transação."""


def new_example(label: str, items: str = "") -> Example:
    example = Example.create(label=label, category=Category.STANDARD, now=NOW)
    for name in (name for name in items.split(", ") if name):
        example.add_item(name)
    return example


async def add_in_transaction(backend: Backend, example: Example) -> None:
    async with backend.unit_of_work.transaction("contract_add"):
        await backend.repository.add(example)


@pytest.fixture
def examples() -> dict[str, Example]:
    return {}


@given(
    parsers.parse('um Example "{label}" com os itens "{items}" gravado numa transação'),
    target_fixture="example",
)
def _(run: Run, backend: Backend, examples: dict[str, Example], label: str, items: str) -> Example:
    example = new_example(label, items)
    run(add_in_transaction(backend, example))
    examples[label] = example
    return example


@when("leio esse Example", target_fixture="outcome")
def _(run: Run, backend: Backend, example: Example) -> Example | None:
    found: Example | None = run(backend.repository.get(example.id))
    return found


@when("leio um Example que não existe", target_fixture="outcome")
def _(run: Run, backend: Backend) -> Example | None:
    found: Example | None = run(backend.repository.get(ExampleId(uuid4())))
    return found


@when(parsers.parse('gravo outro Example "{label}" numa transação'), target_fixture="outcome")
def _(run: Run, backend: Backend, label: str) -> None | LabelTaken:
    try:
        run(add_in_transaction(backend, new_example(label)))
    except LabelTaken as error:
        return error
    return None


@when(parsers.parse('gravo um Example "{label}" fora de uma transação'), target_fixture="outcome")
def _(run: Run, backend: Backend, label: str) -> None | OutsideUnitOfWork:
    try:
        run(backend.repository.add(new_example(label)))
    except OutsideUnitOfWork as error:
        return error
    return None


@when(parsers.parse('gravo um Example "{label}" numa transação que falha depois'))
def _(run: Run, backend: Backend, label: str) -> None:
    async def failing() -> None:
        async with backend.unit_of_work.transaction("contract_failing"):
            await backend.repository.add(new_example(label))
            raise Boom()

    with pytest.raises(Boom):
        run(failing())


@when(
    parsers.parse('arquivo "{label}" e removo os arquivados, numa transação'),
    target_fixture="outcome",
)
def _(run: Run, backend: Backend, examples: dict[str, Example], label: str) -> int:
    async def archive_and_purge() -> int:
        async with backend.unit_of_work.transaction("contract_purge"):
            stored = await backend.repository.get(examples[label].id)
            assert stored is not None
            stored.archive(now=NOW)
            await backend.repository.save(stored)
            return await backend.repository.remove_archived()

    removed: int = run(archive_and_purge())
    return removed


@then(
    parsers.parse(
        'ele volta com o nome "{label}", a categoria "{category}" e os itens "{items}"'
    )
)
def _(outcome: Example | None, label: str, category: str, items: str) -> None:
    assert outcome is not None
    assert (outcome.label, outcome.category) == (label, Category(category))
    assert [(item.name, item.position) for item in outcome.items] == [
        (name, position) for position, name in enumerate(items.split(", "))
    ]
    assert outcome.get_uncommitted_events() == set()


@then("nada volta")
def _(outcome: Example | None) -> None:
    assert outcome is None


@then(parsers.parse("a limpeza removeu {count:d} Example"))
def _(outcome: int, count: int) -> None:
    assert outcome == count


@then(parsers.parse('a listagem tem os nomes "{names}"'))
def _(run: Run, backend: Backend, names: str) -> None:
    summaries = run(backend.reader.list_summaries(limit=100))
    assert [summary.label for summary in summaries] == names.split(", ")


@then("a listagem está vazia")
def _(run: Run, backend: Backend) -> None:
    assert run(backend.reader.list_summaries(limit=100)) == []

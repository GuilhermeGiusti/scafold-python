from datetime import UTC, datetime

from pytest_bdd import given, parsers, scenarios, then, when

from scafold.domain.bounded_context_example.aggregates.example import Example
from scafold.domain.bounded_context_example.entities.example_item import ExampleItem
from scafold.domain.bounded_context_example.errors.duplicate_item import DuplicateItem
from scafold.domain.bounded_context_example.errors.invalid_label import InvalidLabel
from scafold.domain.bounded_context_example.errors.invalid_transition import InvalidTransition
from scafold.domain.bounded_context_example.value_objects.category import Category

scenarios("domain/example.feature")

NOW = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)


def create(label: str, category: Category = Category.STANDARD) -> Example | InvalidLabel:
    try:
        return Example.create(label=label, category=category, now=NOW)
    except InvalidLabel as error:  # só o erro esperado vira resultado
        return error


def event_names(example: Example) -> list[str]:
    """O fato de cada evento registrado: o último trecho de ``name()``."""
    return sorted(event.name().rsplit(".", 1)[-1] for event in example.get_uncommitted_events())


@given(parsers.parse('um Example "{label}" com o item "{item}"'), target_fixture="example")
def _(label: str, item: str) -> Example:
    example = Example.create(label=label, category=Category.STANDARD, now=NOW)
    example.add_item(item)
    return example


@given(parsers.parse('um Example "{label}" arquivado'), target_fixture="example")
def _(label: str) -> Example:
    example = Example.create(label=label, category=Category.STANDARD, now=NOW)
    example.archive(now=NOW)
    return example


@when(
    parsers.parse('crio um Example com o nome "{label}" na categoria "{category}"'),
    target_fixture="outcome",
)
def _(label: str, category: str) -> Example | InvalidLabel:
    return create(label, Category(category))


@when("crio um Example com um nome só de espaços", target_fixture="outcome")
def _() -> Example | InvalidLabel:
    return create("    ")


@when(
    parsers.parse("crio um Example com um nome de {length:d} caracteres"),
    target_fixture="outcome",
)
def _(length: int) -> Example | InvalidLabel:
    return create("x" * length)


@when(parsers.parse('adiciono o item "{name}"'), target_fixture="outcome")
def _(example: Example, name: str) -> ExampleItem | DuplicateItem | InvalidTransition:
    try:
        return example.add_item(name)
    except (DuplicateItem, InvalidTransition) as error:
        return error


@when(parsers.parse('arquivo o Example em "{instant}"'), target_fixture="outcome")
def _(example: Example, instant: str) -> None | InvalidTransition:
    try:
        example.archive(now=datetime.fromisoformat(instant))
    except InvalidTransition as error:
        return error
    return None


@then(parsers.parse('o Example tem o nome "{label}" e a categoria "{category}"'))
def _(outcome: Example | InvalidLabel, label: str, category: str) -> None:
    assert isinstance(outcome, Example)
    assert (outcome.label, outcome.category) == (label, Category(category))


@then("o Example é criado")
def _(outcome: Example | InvalidLabel) -> None:
    assert isinstance(outcome, Example)


@then(parsers.parse('o Example criado registrou os eventos "{names}"'))
def _(outcome: Example | InvalidLabel, names: str) -> None:
    assert isinstance(outcome, Example)
    assert event_names(outcome) == sorted(names.split(", "))


@then(parsers.parse('o Example registrou os eventos "{names}"'))
def _(example: Example, names: str) -> None:
    assert event_names(example) == sorted(names.split(", "))


@then(parsers.parse('o Example tem os itens "{names}", nesta ordem'))
def _(example: Example, names: str) -> None:
    assert [(item.name, item.position) for item in example.items] == [
        (name, position) for position, name in enumerate(names.split(", "))
    ]


@then(parsers.parse('o Example está arquivado desde "{instant}"'))
def _(example: Example, instant: str) -> None:
    assert example.archived_at == datetime.fromisoformat(instant)

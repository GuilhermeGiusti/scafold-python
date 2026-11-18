from uuid import UUID

from pytest_bdd import parsers, scenarios, then, when

from scafold.domain.bounded_context_example.errors.duplicate_item import DuplicateItem
from scafold.domain.bounded_context_example.errors.invalid_label import InvalidLabel
from scafold.domain.bounded_context_example.errors.label_taken import LabelTaken
from scafold.domain.bounded_context_example.value_objects.category import Category
from scafold.domain.bounded_context_example.value_objects.example_id import ExampleId

from ..conftest import Run
from ..support.scene import Scene
from .conftest import create, items_of

scenarios("applications/create_example.feature")

type Outcome = UUID | InvalidLabel | DuplicateItem | LabelTaken


@when(
    parsers.parse('crio o Example "{label}" com os itens "{items}"'), target_fixture="outcome"
)
def _(run: Run, scene: Scene, label: str, items: str) -> Outcome:
    try:
        return create(run, scene, label, items_of(items))
    except (InvalidLabel, DuplicateItem, LabelTaken) as error:
        return error


@then(
    parsers.parse(
        'o Example gravado tem o nome "{label}", a categoria "{category}" e {count:d} itens'
    )
)
def _(scene: Scene, outcome: Outcome, label: str, category: str, count: int) -> None:
    assert isinstance(outcome, UUID)
    stored = scene.store.examples[ExampleId(outcome)]
    assert (stored.label, stored.category, len(stored.items)) == (label, Category(category), count)


@then(parsers.parse('a única transação aberta foi "{name}", e ela commitou'))
def _(scene: Scene, name: str) -> None:
    assert (scene.unit_of_work.opened, scene.unit_of_work.committed) == ([name], [name])


@then(parsers.parse('a outbox guarda o evento "{event_type}" para o destino "{destination}"'))
def _(scene: Scene, event_type: str, destination: str) -> None:
    [event] = scene.store.integration_events
    assert (event.event_type, event.destination) == (event_type, destination)


@then(parsers.parse("a outbox guarda {count:d} evento de integração"))
def _(scene: Scene, count: int) -> None:
    assert len(scene.store.integration_events) == count


@then("nenhuma transação foi aberta")
def _(scene: Scene) -> None:
    assert scene.unit_of_work.opened == []

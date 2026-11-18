from uuid import UUID

from pytest_bdd import parsers, scenarios, then, when

from scafold.applications.errors.example_not_found import ExampleNotFound
from scafold.applications.queries.example_summary import ExampleSummary
from scafold.applications.queries.example_view import ExampleView
from scafold.applications.queries.get_example_query import GetExampleQuery
from scafold.applications.queries.list_examples_query import ListExamplesQuery

from ..conftest import Run
from ..support.scene import Scene

scenarios("applications/read_examples.feature")


def get(run: Run, scene: Scene, example_id: UUID) -> ExampleView | ExampleNotFound:
    try:
        view: ExampleView = run(
            scene.use_cases.get_example.execute(GetExampleQuery(example_id=example_id))
        )
    except ExampleNotFound as error:
        return error
    return view


def listing(run: Run, scene: Scene, limit: int) -> list[ExampleSummary]:
    summaries: list[ExampleSummary] = run(
        scene.use_cases.list_examples.execute(ListExamplesQuery(limit=limit))
    )
    return summaries


@when("consulto esse Example", target_fixture="outcome")
def _(run: Run, scene: Scene, example_id: UUID) -> ExampleView | ExampleNotFound:
    return get(run, scene, example_id)


@when(parsers.parse('consulto o Example "{example_id}"'), target_fixture="outcome")
def _(run: Run, scene: Scene, example_id: str) -> ExampleView | ExampleNotFound:
    return get(run, scene, UUID(example_id))


@when(parsers.parse("listo até {limit:d} Examples"), target_fixture="outcome")
def _(run: Run, scene: Scene, limit: int) -> list[ExampleSummary]:
    return listing(run, scene, limit)


@when("removo os Examples arquivados")
def _(run: Run, scene: Scene) -> None:
    run(scene.use_cases.purge_archived_examples.execute())


@then(parsers.parse('a consulta devolve o nome "{label}" e os itens "{items}"'))
def _(outcome: ExampleView | ExampleNotFound, label: str, items: str) -> None:
    assert isinstance(outcome, ExampleView)
    assert outcome.label == label
    assert [item.name for item in outcome.items] == items.split(", ")


@then(parsers.parse('a listagem devolve os nomes "{names}"'))
def _(outcome: list[ExampleSummary], names: str) -> None:
    assert [summary.label for summary in outcome] == names.split(", ")


@then(parsers.parse('a listagem completa tem os nomes "{names}"'))
def _(run: Run, scene: Scene, names: str) -> None:
    assert [summary.label for summary in listing(run, scene, 100)] == names.split(", ")


@then(parsers.parse('a última transação aberta foi "{name}"'))
def _(scene: Scene, name: str) -> None:
    assert scene.unit_of_work.opened[-1] == name

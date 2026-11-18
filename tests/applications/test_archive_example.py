from datetime import datetime
from uuid import UUID

from pytest_bdd import parsers, scenarios, then, when

from scafold.applications.commands.archive_example_command import ArchiveExampleCommand
from scafold.applications.errors.example_not_found import ExampleNotFound
from scafold.domain.bounded_context_example.errors.invalid_transition import InvalidTransition
from scafold.domain.bounded_context_example.value_objects.example_id import ExampleId

from ..conftest import Run
from ..support.scene import Scene

scenarios("applications/archive_example.feature")


def archive(run: Run, scene: Scene, example_id: UUID) -> None | InvalidTransition | ExampleNotFound:
    try:
        run(scene.use_cases.archive_example.execute(ArchiveExampleCommand(example_id=example_id)))
    except (InvalidTransition, ExampleNotFound) as error:
        return error
    return None


@when("arquivo esse Example", target_fixture="outcome")
def _(run: Run, scene: Scene, example_id: UUID) -> None | InvalidTransition | ExampleNotFound:
    return archive(run, scene, example_id)


@when(parsers.parse('arquivo o Example "{example_id}"'), target_fixture="outcome")
def _(run: Run, scene: Scene, example_id: str) -> None | InvalidTransition | ExampleNotFound:
    return archive(run, scene, UUID(example_id))


@then(parsers.parse('o Example gravado está arquivado desde "{instant}"'))
def _(scene: Scene, example_id: UUID, instant: str) -> None:
    assert scene.store.examples[ExampleId(example_id)].archived_at == datetime.fromisoformat(
        instant
    )

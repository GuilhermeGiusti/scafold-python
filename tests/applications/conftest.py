"""Steps compartilhados pelos cenários de aplicação: o estado gravado antes da ação."""

from __future__ import annotations

from uuid import UUID

from pytest_bdd import given, parsers, then

from scafold.applications.commands.archive_example_command import ArchiveExampleCommand
from scafold.applications.commands.create_example_command import CreateExampleCommand

from ..conftest import Run
from ..support.scene import Scene


def items_of(text: str) -> tuple[str, ...]:
    """``"Capa, Sumário"`` vira ``("Capa", "Sumário")``."""
    return tuple(name for name in text.split(", ") if name)


def create(run: Run, scene: Scene, label: str, items: tuple[str, ...] = ()) -> UUID:
    example_id: UUID = run(
        scene.use_cases.create_example.execute(CreateExampleCommand(label=label, item_names=items))
    )
    return example_id


@given(parsers.parse('um Example "{label}" já gravado'), target_fixture="example_id")
def _(run: Run, scene: Scene, label: str) -> UUID:
    return create(run, scene, label)


@given(
    parsers.parse('um Example "{label}" já gravado com os itens "{items}"'),
    target_fixture="example_id",
)
def _(run: Run, scene: Scene, label: str, items: str) -> UUID:
    return create(run, scene, label, items_of(items))


@given(parsers.parse('um Example "{label}" já gravado e arquivado'), target_fixture="example_id")
def _(run: Run, scene: Scene, label: str) -> UUID:
    example_id = create(run, scene, label)
    run(scene.use_cases.archive_example.execute(ArchiveExampleCommand(example_id=example_id)))
    return example_id


@then(parsers.parse('foram despachados os eventos "{names}"'))
def _(scene: Scene, names: str) -> None:
    dispatched = sorted(event.name().rsplit(".", 1)[-1] for event in scene.dispatcher.dispatched)
    assert dispatched == sorted(names.split(", "))

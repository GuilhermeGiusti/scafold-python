"""Mapper de entrada da borda Streamlit: os valores do formulário para command."""

from __future__ import annotations

from uuid import UUID

from scafold.applications.commands.archive_example_command import ArchiveExampleCommand
from scafold.applications.commands.create_example_command import CreateExampleCommand


class ExampleFormMapper:
    """Traduz o que a tela tem (texto livre, uma linha por item) no que o use case recebe."""

    def to_create_command(self, label: str, items_text: str) -> CreateExampleCommand:
        names = tuple(line.strip() for line in items_text.splitlines() if line.strip())
        return CreateExampleCommand(label=label, item_names=names)

    def to_archive_command(self, example_id: str) -> ArchiveExampleCommand:
        return ArchiveExampleCommand(example_id=UUID(example_id))

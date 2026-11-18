"""Command: o pedido para arquivar um Example."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class ArchiveExampleCommand:
    """O id chega como ``UUID``, como veio de fora. Quem o converte no tipo do domínio é o use
    case."""

    example_id: UUID

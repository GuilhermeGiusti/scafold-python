"""Query: o pedido para ler um Example."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class GetExampleQuery:
    """Mesmo formato de um command, intenção oposta: pede dado e não altera estado."""

    example_id: UUID

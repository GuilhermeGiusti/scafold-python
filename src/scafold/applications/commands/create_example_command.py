"""Command: o pedido para criar um Example com seus itens."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateExampleCommand:
    """Um command é a intenção de mudar o estado, congelada.

    Só carrega dados: não valida regra de negócio, não acessa repositório e não sabe quem o
    executa. ``frozen=True`` impede que alguém altere o pedido entre quem o criou (o controller,
    a CLI, a tela, o teste) e o use case que o executa.
    """

    label: str
    item_names: tuple[str, ...] = ()

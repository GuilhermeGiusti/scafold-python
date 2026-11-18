"""Fila vazia, como estado normal do ciclo de drenagem."""

from __future__ import annotations


class NoPendingMessage(LookupError):
    """Nenhuma mensagem pendente disponível para o carimbo pedido.

    É exceção própria, e não ``None`` repassado do driver: fila vazia é estado normal, e a
    drenagem a trata dentro da transação, que commita vazia em vez de ser revertida.
    """

    def __init__(self) -> None:
        super().__init__("nenhuma mensagem pendente")

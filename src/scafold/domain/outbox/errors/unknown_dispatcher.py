"""Gravador da outbox montado com um carimbo que ninguém drena."""

from __future__ import annotations


class UnknownDispatcher(ValueError):
    """O carimbo está fora de ``KNOWN_DISPATCHERS``: a linha gravada nunca seria drenada."""

    def __init__(self) -> None:
        super().__init__("o gravador da outbox recebeu um dispatcher desconhecido")

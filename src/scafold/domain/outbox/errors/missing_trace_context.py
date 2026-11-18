"""Gravação na outbox sem span corrente."""

from __future__ import annotations


class MissingTraceContext(RuntimeError):
    """Sem span corrente, o ``correlation_id`` da mensagem ficaria vazio.

    O identificador de correlação é o id do trace (ADR-012). Quem abre o span é a borda do
    processo ou o decorator do use case, que sempre envolve quem grava.
    """

    def __init__(self) -> None:
        super().__init__("gravacao na outbox sem span corrente")

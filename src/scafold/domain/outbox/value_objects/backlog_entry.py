"""O backlog de um carimbo: quantas mensagens esperam e há quanto tempo a mais antiga espera."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class BacklogEntry:
    """Só vêm carimbos com pendências. Quem publica a métrica semeia os demais com zero."""

    dispatcher: str
    pending: int
    oldest_age_seconds: float

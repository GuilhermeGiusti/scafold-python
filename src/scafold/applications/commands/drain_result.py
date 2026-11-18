"""O resultado de um ciclo de drenagem da outbox."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class DrainResult:
    #: Mensagens marcadas `PUBLISHED` no ciclo.
    published: int
    #: Mensagens reagendadas depois de uma falha transitória.
    retried: int
    #: Mensagens que viraram `DEAD`, por falha permanente ou por tentativas esgotadas.
    dead: int
    #: A duração do ciclo, em segundos.
    seconds: float

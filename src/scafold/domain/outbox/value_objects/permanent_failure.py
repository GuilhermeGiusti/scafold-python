"""O desfecho "não melhora com nova tentativa"."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PermanentFailure:
    """Falha que não melhora com nova tentativa. A drenagem mata a mensagem na hora."""

    detail: str

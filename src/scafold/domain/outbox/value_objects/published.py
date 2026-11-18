"""O desfecho "o broker aceitou"."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Published:
    """O broker confirmou a publicação. A drenagem marca `PUBLISHED`."""

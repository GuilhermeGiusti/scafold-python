"""Uma falha de envio, como fica registrada no histórico da mensagem."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

#: Os valores aceitos pela restrição `ck_outbox_error_error_kind`.
FAILURE_TRANSIENT = "TRANSIENTE"
FAILURE_PERMANENT = "PERMANENTE"


@dataclass(frozen=True, slots=True, kw_only=True)
class Failure:
    """Uma linha de ``outbox_error``. ``detail`` vem da Strategy e nunca repete o payload."""

    message_id: UUID
    #: O número desta tentativa: as tentativas anteriores mais um.
    attempt_no: int
    #: `FAILURE_TRANSIENT` ou `FAILURE_PERMANENT`.
    kind: str
    detail: str

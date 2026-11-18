"""O desfecho "pode dar certo depois"."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TransientFailure:
    """Falha de momento. A drenagem reagenda até ``MAX_ATTEMPTS`` e então mata a mensagem.

    ``detail`` vai só para o histórico ``outbox_error``, com até 500 caracteres, e nunca traz o
    payload. Ele nunca vai para métrica, log nem span.
    """

    detail: str

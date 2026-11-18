"""Porta do publicador: a Strategy de um broker (ADR-006).

Uma Strategy por broker. Ela publica e relata, e só isso: nunca lança, nunca conta tentativas,
nunca grava no banco e nunca abre span. Quem decide o destino da mensagem é a drenagem; quem abre
o span de envio é um envoltório na infraestrutura (``TracedDispatcher``).

Mora no domínio porque quem a consome é a drenagem, na camada de aplicação. As Strategies
concretas moram em ``infrastructure/brokers/``.
"""

from __future__ import annotations

from typing import Protocol

from scafold.domain.outbox.value_objects.dispatch_outcome import DispatchOutcome
from scafold.domain.outbox.value_objects.pending_message import PendingMessage


class IDispatcher(Protocol):
    @property
    def name(self) -> str:
        """O carimbo das mensagens que este publicador entrega."""
        ...

    async def dispatch(self, message: PendingMessage) -> DispatchOutcome:
        """Publica a mensagem e relata o resultado, sem lançar."""
        ...

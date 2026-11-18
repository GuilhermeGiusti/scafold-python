"""Recusa de um evento de integração incompleto."""

from __future__ import annotations


class InvalidIntegrationEvent(ValueError):
    """Evento incompleto, ou com o destino lógico fora do formato. Recusado antes do banco.

    ``reason`` é o nome do campo recusado. A mensagem nunca repete o valor recebido: o evento
    pode carregar dado pessoal, e a mensagem de uma exceção é o caminho mais curto até um log.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(f"evento de integracao recusado no campo {reason}")
        self.reason = reason

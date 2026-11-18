"""Contrato de métricas de use case."""

from __future__ import annotations

from typing import Literal, Protocol

type UseCaseStatus = Literal["ok", "error"]

#: O `error_type` de uma execução que terminou sem exceção.
NO_ERROR = "none"


class IUseCaseMetrics(Protocol):
    """Porta de métricas consumida só pelos decorators de observabilidade.

    O use case não fala de métrica: quem mede é o decorator que o envolve na montagem. Complementa
    a métrica de transações e queries, medida pela Unit of Work. Os rótulos são o nome literal do
    use case, o status e o nome da classe da exceção. Id, dado do command e mensagem de erro ficam
    fora de todo sinal.
    """

    def use_case_executed(
        self,
        *,
        use_case: str,
        status: UseCaseStatus,
        error_type: str,
        duration_seconds: float,
    ) -> None:
        """Métricas ``use_case_executions_total`` e ``use_case_duration_seconds``."""
        ...

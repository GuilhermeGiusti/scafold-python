"""Contrato da métrica de erro de tradução dos adaptadores de serviço externo."""

from __future__ import annotations

from typing import Protocol


class ITranslationErrorMetrics(Protocol):
    """Porta de métricas consumida só pelos adaptadores de ``infrastructure/external/``.

    O único rótulo é ``gateway``, o nome fixo do adaptador em snake_case. O termo que o fornecedor
    mandou NÃO vira rótulo: é escolhido por um terceiro, sem limite de valores.
    """

    def translation_failed(self, *, gateway: str) -> None:
        """Métrica ``external_translation_errors_total`` (contador por ``gateway``)."""
        ...

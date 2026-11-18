"""Adaptador da porta ``ICategoryGateway`` sobre a API externa."""

from __future__ import annotations

import logging

from scafold.domain.bounded_context_example.value_objects.category import Category
from scafold.infrastructure.external.errors.unmapped_payload import UnmappedPayload
from scafold.infrastructure.external.fake_category_api import FakeCategoryApi
from scafold.infrastructure.external.mappers.category_payload_mapper import (
    CategoryPayloadMapper,
)
from scafold.infrastructure.external.metrics.translation_error_metrics import (
    ITranslationErrorMetrics,
)

logger = logging.getLogger(__name__)

#: O rótulo deste adaptador em `external_translation_errors_total`. Literal fixo: renomear a
#: classe não pode quebrar o histórico da série.
GATEWAY_NAME = "category_gateway"


class ExternalCategoryGateway:
    """Implementa ``ICategoryGateway``. O mapper e a métrica chegam pelo construtor."""

    def __init__(
        self,
        *,
        api: FakeCategoryApi,
        mapper: CategoryPayloadMapper,
        metrics: ITranslationErrorMetrics,
    ) -> None:
        self._api = api
        self._mapper = mapper
        self._metrics = metrics

    async def classify(self, label: str) -> Category:
        response = await self._api.classify(self._mapper.to_request_payload(label))
        try:
            return self._mapper.to_category(response)
        except UnmappedPayload:
            # O fornecedor mudou o contrato: é defeito, e sobe. O adaptador registra no log e conta
            # na métrica antes de relançar. O termo desconhecido não vira rótulo.
            logger.exception("payload do fornecedor sem traducao")
            self._metrics.translation_failed(gateway=GATEWAY_NAME)
            raise

"""API externa de mentira, com o vocabulário do fornecedor.

Faz o papel do cliente HTTP de um fornecedor real. Num projeto de verdade, este arquivo vira o
cliente do fornecedor (com timeout e retentativa), e o resto do adaptador não muda.
"""

from __future__ import annotations

from typing import TypedDict


class ClassifyRequestPayload(TypedDict):
    text: str


class ClassifyResponsePayload(TypedDict):
    tier: str
    confidence: str


class FakeCategoryApi:
    async def classify(self, payload: ClassifyRequestPayload) -> ClassifyResponsePayload:
        tier = "GOLD" if "premium" in payload["text"].lower() else "BASIC"
        return {"tier": tier, "confidence": "0.93"}

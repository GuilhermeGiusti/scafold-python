"""Schema HTTP do health check."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from scafold.infrastructure.rest.shared.schemas import ResponseSchema


class HealthResponse(ResponseSchema):
    """O processo está de pé e atende requisições."""

    status: Annotated[Literal["ok"], Field(examples=["ok"])]
    """Sempre `ok` quando a resposta chega: quem não está de pé não responde."""

"""Identificador de um pedido."""

from __future__ import annotations

from typing import NewType
from uuid import UUID

OrderId = NewType("OrderId", UUID)

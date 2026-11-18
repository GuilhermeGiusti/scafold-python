"""Item de um pedido: value object imutável, validado na criação."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from scafold.domain.bounded_context_order.errors.invalid_quantity import InvalidQuantity


@dataclass(frozen=True, slots=True)
class OrderItem:
    """Se o objeto existe, ele é válido: a regra fica no ``__post_init__``."""

    sku: str
    quantity: int
    unit_price: Decimal

    def __post_init__(self) -> None:
        if self.quantity < 1:
            raise InvalidQuantity("a quantidade precisa ser de pelo menos 1")

    @property
    def subtotal(self) -> Decimal:
        return self.unit_price * self.quantity

"""Estado modelado por tipos (ADR-007): o ciclo de vida de um pedido, um tipo por estado.

Com um tipo único e um campo ``status``, a transição proibida vira um ``if`` que só falha em
runtime, e o campo que só existe em alguns estados vira opcional. Aqui cada estado é um tipo com
os campos que existem nele, a transição é um método do estado de origem que devolve o estado de
destino, e a transição proibida é ausência de método. O mypy aponta os dois erros antes de rodar.

| Método                        | De             | Para             |
|-------------------------------|----------------|------------------|
| ``PlacedOrder.approve_payment`` | ``PlacedOrder``  | ``PaidOrder``      |
| ``PlacedOrder.refuse_payment``  | ``PlacedOrder``  | ``CancelledOrder`` |
| ``PaidOrder.ship``              | ``PaidOrder``    | ``ShippedOrder``   |
| ``PaidOrder.cancel``            | ``PaidOrder``    | ``CancelledOrder`` |
| ``ShippedOrder.deliver``        | ``ShippedOrder`` | ``DeliveredOrder`` |

``ShippedOrder`` não tem ``cancel``: pedido enviado não cancela.

Este padrão convive com o ``AggregateRoot`` (ADR-001 e ADR-002): os estados são imutáveis e não
registram eventos. Se o modelo emitir eventos, a transição devolve o par ``(estado, evento)`` e
quem chamou persiste o estado e despacha o evento. As garantias valem só com o mypy rodando.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import assert_never

from scafold.domain.bounded_context_order.errors.empty_order import EmptyOrder
from scafold.domain.bounded_context_order.errors.invalid_tracking_code import (
    InvalidTrackingCode,
)
from scafold.domain.bounded_context_order.value_objects.order_id import OrderId
from scafold.domain.bounded_context_order.value_objects.order_item import OrderItem

_TRACKING_CODE = re.compile(r"[A-Z]{2}\d{9}[A-Z]{2}")


def _check_tracking_code(value: str) -> None:
    if not _TRACKING_CODE.fullmatch(value):
        raise InvalidTrackingCode("codigo de rastreio fora do formato")


@dataclass(frozen=True, slots=True)
class _OrderBase:
    """O que todo estado tem em comum. Não é um estado: não pode ser instanciada."""

    id: OrderId
    items: tuple[OrderItem, ...]

    def __post_init__(self) -> None:
        if type(self) is _OrderBase:
            raise TypeError("_OrderBase nao e um estado de pedido; use um dos tipos de Order")
        if not self.items:
            raise EmptyOrder("pedido sem itens")

    @property
    def total(self) -> Decimal:
        return sum((item.subtotal for item in self.items), Decimal(0))


@dataclass(frozen=True, slots=True)
class PlacedOrder(_OrderBase):
    shipping_address: str
    placed_at: datetime

    def approve_payment(self, authorization_code: str, at: datetime) -> PaidOrder:
        return PaidOrder(
            id=self.id,
            items=self.items,
            shipping_address=self.shipping_address,
            authorization_code=authorization_code,
            paid_at=at,
        )

    def refuse_payment(self, reason: str, at: datetime) -> CancelledOrder:
        return CancelledOrder(id=self.id, items=self.items, reason=reason, cancelled_at=at)


@dataclass(frozen=True, slots=True)
class PaidOrder(_OrderBase):
    shipping_address: str
    authorization_code: str
    paid_at: datetime

    def ship(self, tracking_code: str, at: datetime) -> ShippedOrder:
        return ShippedOrder(
            id=self.id,
            items=self.items,
            shipping_address=self.shipping_address,
            tracking_code=tracking_code,
            shipped_at=at,
        )

    def cancel(self, reason: str, at: datetime) -> CancelledOrder:
        return CancelledOrder(id=self.id, items=self.items, reason=reason, cancelled_at=at)


@dataclass(frozen=True, slots=True)
class ShippedOrder(_OrderBase):
    """Só os estados enviado e entregue têm ``tracking_code``, e a regra dele fica aqui."""

    shipping_address: str
    tracking_code: str
    shipped_at: datetime

    def __post_init__(self) -> None:
        _OrderBase.__post_init__(self)
        _check_tracking_code(self.tracking_code)

    def deliver(self, at: datetime) -> DeliveredOrder:
        return DeliveredOrder(
            id=self.id, items=self.items, tracking_code=self.tracking_code, delivered_at=at
        )


@dataclass(frozen=True, slots=True)
class DeliveredOrder(_OrderBase):
    tracking_code: str
    delivered_at: datetime

    def __post_init__(self) -> None:
        _OrderBase.__post_init__(self)
        _check_tracking_code(self.tracking_code)


@dataclass(frozen=True, slots=True)
class CancelledOrder(_OrderBase):
    reason: str
    cancelled_at: datetime


#: Onde o código aceita qualquer estado. Descubra o estado com `match` antes de chamar transição.
type Order = PlacedOrder | PaidOrder | ShippedOrder | DeliveredOrder | CancelledOrder


def label(order: Order) -> str:
    """O ``match`` exaustivo: um estado novo sem o seu ``case`` vira erro do mypy."""
    match order:
        case PlacedOrder():
            return "aguardando pagamento"
        case PaidOrder():
            return "pago"
        case ShippedOrder(tracking_code=code):
            return f"enviado: {code}"
        case DeliveredOrder():
            return "entregue"
        case CancelledOrder(reason=reason):
            return f"cancelado: {reason}"
        case _:
            assert_never(order)

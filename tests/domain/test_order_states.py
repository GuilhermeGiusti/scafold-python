from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from pytest_bdd import given, parsers, scenarios, then, when

from scafold.domain.bounded_context_order.aggregates.order import Order, PlacedOrder, label
from scafold.domain.bounded_context_order.errors.empty_order import EmptyOrder
from scafold.domain.bounded_context_order.errors.invalid_quantity import InvalidQuantity
from scafold.domain.bounded_context_order.errors.invalid_tracking_code import (
    InvalidTrackingCode,
)
from scafold.domain.bounded_context_order.value_objects.order_id import OrderId
from scafold.domain.bounded_context_order.value_objects.order_item import OrderItem

scenarios("domain/order_states.feature")

AT = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)


def place(items: tuple[OrderItem, ...]) -> PlacedOrder:
    return PlacedOrder(
        id=OrderId(uuid4()), items=items, shipping_address="Rua A, 1", placed_at=AT
    )


@given(
    parsers.parse('um pedido feito com {quantity:d} unidades de "{sku}" a {price}'),
    target_fixture="placed",
)
def _(quantity: int, sku: str, price: str) -> PlacedOrder:
    return place((OrderItem(sku=sku, quantity=quantity, unit_price=Decimal(price)),))


@when(
    parsers.parse('o pagamento é aprovado e o pedido é enviado com o código "{code}"'),
    target_fixture="outcome",
)
def _(placed: PlacedOrder, code: str) -> Order | InvalidTrackingCode:
    paid = placed.approve_payment("AUTH-1", AT)
    try:
        return paid.ship(code, AT)
    except InvalidTrackingCode as error:
        return error


@when(parsers.parse('o pagamento é recusado por "{reason}"'), target_fixture="outcome")
def _(placed: PlacedOrder, reason: str) -> Order:
    return placed.refuse_payment(reason, AT)


@when("faço um pedido sem itens", target_fixture="outcome")
def _() -> PlacedOrder | EmptyOrder:
    try:
        return place(())
    except EmptyOrder as error:
        return error


@when(
    parsers.parse('faço um pedido com {quantity:d} unidades de "{sku}" a {price}'),
    target_fixture="outcome",
)
def _(quantity: int, sku: str, price: str) -> PlacedOrder | InvalidQuantity:
    try:
        return place((OrderItem(sku=sku, quantity=quantity, unit_price=Decimal(price)),))
    except InvalidQuantity as error:
        return error


@then(parsers.parse('o pedido está "{text}"'))
def _(outcome: Order | Exception, text: str) -> None:
    assert not isinstance(outcome, Exception)
    assert label(outcome) == text


@then(parsers.parse('o pedido feito continua "{text}"'))
def _(placed: PlacedOrder, text: str) -> None:
    assert label(placed) == text


@then(parsers.parse("o total do pedido é {total}"))
def _(outcome: Order | Exception, total: str) -> None:
    assert not isinstance(outcome, Exception)
    assert outcome.total == Decimal(total)

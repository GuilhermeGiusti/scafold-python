"""Erro de domínio: pedido sem itens."""


class EmptyOrder(Exception):
    """Todo pedido tem pelo menos um item, em qualquer estado."""

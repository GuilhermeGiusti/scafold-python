"""Erro de domínio: quantidade de item fora da regra."""


class InvalidQuantity(Exception):
    """Todo item de pedido tem quantidade de pelo menos 1."""

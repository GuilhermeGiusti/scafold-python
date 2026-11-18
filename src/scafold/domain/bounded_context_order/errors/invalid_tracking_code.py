"""Erro de domínio: código de rastreio fora do formato."""


class InvalidTrackingCode(Exception):
    """O código de rastreio tem duas letras, nove dígitos e duas letras, como ``BR123456789XX``."""

"""Erro de aplicação: o Example pedido não existe."""

from scafold.applications.errors.application_error import ApplicationError


class ExampleNotFound(ApplicationError):
    """É da aplicação, não do domínio: "não existe" é resposta à busca do use case, e não uma
    regra que o agregado conhece."""

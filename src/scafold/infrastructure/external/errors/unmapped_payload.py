"""Erro de infraestrutura: chegou um payload que o mapper não sabe traduzir."""


class UnmappedPayload(Exception):
    """O fornecedor devolveu um termo fora do vocabulário que o mapper conhece.

    Não é erro de domínio nem de aplicação: a falha é do contrato com o fornecedor. Não use
    ``ValueError`` nem erro de aplicação. Chega ao cliente como o 500 genérico do presenter.
    """

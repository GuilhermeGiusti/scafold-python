"""A base dos erros de aplicação deste módulo."""


class ApplicationError(Exception):
    """Todo erro de aplicação herda daqui, e a borda traduz a partir desta base.

    Erro de aplicação é resposta ao pedido ("o que foi pedido não existe"). Regra de negócio
    violada é erro de domínio e não herda daqui. Falha sai como exceção, nunca como ``False`` ou
    ``None``.
    """

"""Erro de domínio: a operação não vale no estado atual do agregado."""


class InvalidTransition(Exception):
    """A operação pedida não é permitida no estado em que o Example está.

    Os erros pertencem ao contexto: outro bounded context tem o seu próprio ``InvalidTransition``
    e não importa este.
    """

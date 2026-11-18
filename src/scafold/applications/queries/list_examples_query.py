"""Query: o pedido para listar Examples."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class ListExamplesQuery:
    """A listagem ganhou paginação, e por isso tem query object.

    Sem filtro nem paginação, o use case seria ``AsyncNullaryUseCase`` e não teria query. A troca
    muda a assinatura de ``execute``, e o mypy aponta todos os chamadores.
    """

    limit: int

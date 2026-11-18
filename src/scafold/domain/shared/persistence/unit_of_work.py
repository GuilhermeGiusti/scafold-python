"""Porta da Unit of Work: a fronteira de transação que o use case de escrita abre."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import Protocol


class IUnitOfWork(Protocol):
    """Abre uma transação com nome.

    O nome identifica a transação nas métricas (``transaction="create_example"``). Ele é um
    literal fixo escolhido por quem abre, em snake_case, igual ao nome do use case sem o sufixo.
    Nunca leva id, rótulo ou outro dado da requisição: cada valor distinto viraria uma série de
    métrica nova.

    Uso::

        async with unit_of_work.transaction("create_example"):
            await repository.add(example)

    Sair do bloco sem erro commita; erro dentro do bloco reverte tudo e sobe para quem abriu. Uma
    transação aberta dentro de outra participa da externa: não há commit parcial.

    Não importa SQLAlchemy: ``write_querier`` e ``querier`` devolvem conexão do driver e por isso
    ficam fora da porta, na ``UnitOfWork`` concreta que repositórios e leitores recebem.
    """

    def transaction(self, name: str) -> AbstractAsyncContextManager[None]: ...

"""Use case sem input e sem retorno: remover os Examples arquivados."""

from __future__ import annotations

import logging

from scafold.applications.shared.use_case import AsyncExecuterUseCase
from scafold.domain.bounded_context_example.repositories.example_repository import (
    IExampleRepository,
)
from scafold.domain.shared.persistence.unit_of_work import IUnitOfWork

TRANSACTION_NAME = "purge_archived_examples"

logger = logging.getLogger(__name__)


class PurgeArchivedExamplesUseCase(AsyncExecuterUseCase):
    """O formato de um job: quem chama ``execute()`` não sabe nada do que ele faz.

    Sem input nem retorno, o que aconteceu só aparece no log e no estado do repositório. O registro
    é de rotina e sai em DEBUG.
    """

    def __init__(self, *, unit_of_work: IUnitOfWork, repository: IExampleRepository) -> None:
        self._unit_of_work = unit_of_work
        self._repository = repository

    async def execute(self) -> None:
        async with self._unit_of_work.transaction(TRANSACTION_NAME):
            removed = await self._repository.remove_archived()
        logger.debug("purge_archived_examples removed=%d", removed)

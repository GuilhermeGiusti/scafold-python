"""Borda Streamlit de Example: a tela que cria, lista e arquiva, pelos mesmos use cases da API.

O Streamlit reexecuta o script inteiro a cada interação e é síncrono. Os use cases são
assíncronos, então a página recebe ``run``, que executa uma corrotina e devolve o resultado: em
produção, o event loop de fundo da montagem (o pool do banco fica preso a um loop só); nos
testes, ``asyncio.run``.
"""

from __future__ import annotations

from collections.abc import Coroutine
from typing import Any, Protocol

import streamlit as st

from scafold.applications.commands.archive_example_command import ArchiveExampleCommand
from scafold.applications.commands.create_example_command import CreateExampleCommand
from scafold.applications.queries.example_summary import ExampleSummary
from scafold.applications.queries.list_examples_query import ListExamplesQuery
from scafold.applications.shared.use_case import AsyncUnitUseCase, AsyncUseCase
from scafold.domain.bounded_context_example.value_objects.example_id import ExampleId
from scafold.infrastructure.streamlit.mappers.example_form_mapper import ExampleFormMapper
from scafold.infrastructure.streamlit.presenters.example_page_presenter import (
    ExamplePagePresenter,
)

#: Quantos Examples a tela lista.
PAGE_SIZE = 50


class Runner(Protocol):
    """Executa uma corrotina até o fim e devolve o resultado."""

    def __call__[T](self, coroutine: Coroutine[Any, Any, T], /) -> T: ...


class ExamplePage:
    def __init__(
        self,
        *,
        create: AsyncUseCase[CreateExampleCommand, ExampleId],
        archive: AsyncUnitUseCase[ArchiveExampleCommand],
        list_all: AsyncUseCase[ListExamplesQuery, list[ExampleSummary]],
        run: Runner,
        mapper: ExampleFormMapper,
        presenter: ExamplePagePresenter,
    ) -> None:
        self._create = create
        self._archive = archive
        self._list_all = list_all
        self._run = run
        self._mapper = mapper
        self._presenter = presenter

    def render(self) -> None:
        st.title("Examples")

        st.subheader("Criar")
        label = st.text_input("Nome", key="label")
        items_text = st.text_area("Itens, um por linha", key="items")
        if st.button("Criar", key="create"):
            self._create_example(label, items_text)

        summaries = self._run(self._list_all.execute(ListExamplesQuery(limit=PAGE_SIZE)))

        st.subheader("Cadastrados")
        if summaries:
            st.dataframe(self._presenter.present_rows(summaries), hide_index=True)
        else:
            st.info("Nenhum Example cadastrado.")

        active = [str(summary.id) for summary in summaries if not summary.archived]
        if active:
            st.subheader("Arquivar")
            chosen = st.selectbox("Example", active, key="archive_id")
            if st.button("Arquivar", key="archive") and chosen is not None:
                self._archive_example(chosen)

    def _create_example(self, label: str, items_text: str) -> None:
        command = self._mapper.to_create_command(label, items_text)
        try:
            example_id = self._run(self._create.execute(command))
        except self._presenter.PRESENTABLE as error:
            st.error(self._presenter.present_error(error))
            return
        st.success(self._presenter.present_created(example_id))

    def _archive_example(self, example_id: str) -> None:
        command = self._mapper.to_archive_command(example_id)
        try:
            self._run(self._archive.execute(command))
        except self._presenter.PRESENTABLE as error:
            st.error(self._presenter.present_error(error))
            return
        st.success(self._presenter.present_archived())

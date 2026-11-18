"""Presenter da borda Streamlit: a saída do use case para a tela, e os erros esperados."""

from __future__ import annotations

from typing import ClassVar

from scafold.applications.errors.application_error import ApplicationError
from scafold.applications.errors.example_not_found import ExampleNotFound
from scafold.applications.queries.example_summary import ExampleSummary
from scafold.domain.bounded_context_example.errors.duplicate_item import DuplicateItem
from scafold.domain.bounded_context_example.errors.invalid_label import InvalidLabel
from scafold.domain.bounded_context_example.errors.invalid_transition import InvalidTransition
from scafold.domain.bounded_context_example.errors.label_taken import LabelTaken
from scafold.domain.bounded_context_example.value_objects.example_id import ExampleId

#: As colunas da tabela, nesta ordem.
COLUMNS = ("Nome", "Itens", "Arquivado", "Id")


class ExamplePagePresenter:
    """As decisões de apresentação da tela: os nomes das colunas e o texto de cada erro."""

    PRESENTABLE: ClassVar[tuple[type[Exception], ...]] = (
        ApplicationError,
        InvalidLabel,
        DuplicateItem,
        InvalidTransition,
        LabelTaken,
    )

    _MESSAGES: ClassVar[tuple[tuple[type[Exception], str], ...]] = (
        (ExampleNotFound, "Example não encontrado."),
        (LabelTaken, "Já existe um Example com esse nome."),
        (DuplicateItem, "A lista de itens repete um nome."),
        (InvalidTransition, "O Example já está arquivado."),
        (InvalidLabel, "O nome não pode ficar vazio."),
        (ApplicationError, "O pedido não pôde ser atendido."),
    )

    def present_created(self, example_id: ExampleId) -> str:
        return f"Example criado: {example_id}"

    def present_archived(self) -> str:
        return "Example arquivado."

    def present_rows(self, summaries: list[ExampleSummary]) -> list[dict[str, object]]:
        return [
            dict(
                zip(
                    COLUMNS,
                    (summary.label, summary.item_count, summary.archived, str(summary.id)),
                    strict=True,
                )
            )
            for summary in summaries
        ]

    def present_error(self, error: Exception) -> str:
        for error_type, message in self._MESSAGES:
            if isinstance(error, error_type):
                return message
        raise error

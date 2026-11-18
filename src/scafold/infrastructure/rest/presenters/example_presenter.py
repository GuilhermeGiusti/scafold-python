"""Presenter de Example: a saída do use case para o response schema, e os erros do agregado."""

from __future__ import annotations

from typing import ClassVar

from scafold.applications.errors.application_error import ApplicationError
from scafold.applications.errors.example_not_found import ExampleNotFound
from scafold.applications.queries.example_summary import ExampleSummary
from scafold.applications.queries.example_view import ExampleView
from scafold.domain.bounded_context_example.errors.duplicate_item import DuplicateItem
from scafold.domain.bounded_context_example.errors.invalid_label import InvalidLabel
from scafold.domain.bounded_context_example.errors.invalid_transition import InvalidTransition
from scafold.domain.bounded_context_example.errors.label_taken import LabelTaken
from scafold.domain.bounded_context_example.value_objects.category import Category
from scafold.domain.bounded_context_example.value_objects.example_id import ExampleId
from scafold.infrastructure.rest.example_schemas import (
    CategoryText,
    ExampleCreatedResponse,
    ExampleItemResponse,
    ExampleListResponse,
    ExampleResponse,
    ExampleSummaryResponse,
)
from scafold.infrastructure.rest.shared.error_presenter import ErrorEntry, ErrorPresenter


class ExamplePresenter(ErrorPresenter):
    """O que é comum a toda borda REST (apresentar e documentar erro) vem de ``ErrorPresenter``.

    Aqui ficam a tabela de erros do agregado e os métodos de saída. As decisões de apresentação
    (os nomes do contrato HTTP, o texto da categoria) são deste presenter, e não do use case.
    """

    PRESENTABLE: ClassVar[tuple[type[Exception], ...]] = (
        ApplicationError,
        InvalidLabel,
        DuplicateItem,
        InvalidTransition,
        LabelTaken,
    )

    _ERRORS: ClassVar[tuple[tuple[type[Exception], ErrorEntry], ...]] = (
        (
            ExampleNotFound,
            ErrorEntry(
                404,
                "example_not_found",
                "Example não encontrado.",
                "Não existe Example com o identificador informado.",
            ),
        ),
        (
            LabelTaken,
            ErrorEntry(
                409,
                "label_taken",
                "Já existe um Example com esse nome.",
                "O nome informado já pertence a outro Example.",
            ),
        ),
        (
            DuplicateItem,
            ErrorEntry(
                409,
                "duplicate_item",
                "A lista de itens repete um nome.",
                "Dois itens do pedido têm o mesmo nome.",
            ),
        ),
        (
            InvalidTransition,
            ErrorEntry(
                409,
                "invalid_transition",
                "A operação não vale no estado atual do Example.",
                "O Example já está arquivado.",
            ),
        ),
        (
            InvalidLabel,
            ErrorEntry(
                400,
                "invalid_label",
                "O nome do Example não cumpre a regra.",
                "O nome, sem os espaços das pontas, fica vazio.",
            ),
        ),
    )

    #: O texto de cada categoria no contrato HTTP. Decisão de apresentação, e não do domínio.
    _CATEGORY_TEXT: ClassVar[dict[Category, CategoryText]] = {
        Category.STANDARD: "standard",
        Category.PREMIUM: "premium",
    }

    def present_created(self, example_id: ExampleId) -> ExampleCreatedResponse:
        return ExampleCreatedResponse(id=example_id)

    def present(self, view: ExampleView) -> ExampleResponse:
        return ExampleResponse(
            id=view.id,
            display_name=view.label,
            category=self._CATEGORY_TEXT[view.category],
            created_at=view.created_at,
            archived_at=view.archived_at,
            items=[
                ExampleItemResponse(id=item.id, name=item.name, position=item.position)
                for item in view.items
            ],
        )

    def present_list(self, summaries: list[ExampleSummary]) -> ExampleListResponse:
        return ExampleListResponse(
            items=[
                ExampleSummaryResponse(
                    id=summary.id,
                    display_name=summary.label,
                    item_count=summary.item_count,
                    archived=summary.archived,
                )
                for summary in summaries
            ]
        )

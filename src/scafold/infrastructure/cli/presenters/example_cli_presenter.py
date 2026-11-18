"""Presenter da borda de linha de comando: a saída do use case em JSON, e os erros esperados."""

from __future__ import annotations

import json
from typing import ClassVar

from scafold.applications.errors.application_error import ApplicationError
from scafold.applications.errors.example_not_found import ExampleNotFound
from scafold.applications.queries.example_summary import ExampleSummary
from scafold.applications.queries.example_view import ExampleView
from scafold.domain.bounded_context_example.errors.duplicate_item import DuplicateItem
from scafold.domain.bounded_context_example.errors.invalid_label import InvalidLabel
from scafold.domain.bounded_context_example.errors.invalid_transition import InvalidTransition
from scafold.domain.bounded_context_example.errors.label_taken import LabelTaken
from scafold.domain.bounded_context_example.value_objects.example_id import ExampleId


class ExampleCliPresenter:
    """Cada borda tem o seu presenter: a linha de comando fala JSON na saída padrão.

    Os erros esperados saem com código e texto do presenter, nunca com ``str(error)``. Um erro fora
    da tabela é defeito e sobe para o ponto de entrada, que o registra no log.
    """

    #: Os erros que são resposta ao pedido.
    PRESENTABLE: ClassVar[tuple[type[Exception], ...]] = (
        ApplicationError,
        InvalidLabel,
        DuplicateItem,
        InvalidTransition,
        LabelTaken,
    )

    _ERRORS: ClassVar[tuple[tuple[type[Exception], str, str], ...]] = (
        (ExampleNotFound, "example_not_found", "Example não encontrado."),
        (LabelTaken, "label_taken", "Já existe um Example com esse nome."),
        (DuplicateItem, "duplicate_item", "A lista de itens repete um nome."),
        (InvalidTransition, "invalid_transition", "A operação não vale no estado atual do Example."),
        (InvalidLabel, "invalid_label", "O nome do Example não cumpre a regra."),
        (ApplicationError, "application_error", "O pedido não pôde ser atendido."),
    )

    def present_created(self, example_id: ExampleId) -> str:
        return _json({"id": str(example_id)})

    def present_done(self) -> str:
        return _json({"status": "ok"})

    def present_view(self, view: ExampleView) -> str:
        return _json(
            {
                "id": str(view.id),
                "label": view.label,
                "category": view.category.value,
                "created_at": view.created_at.isoformat(),
                "archived_at": view.archived_at.isoformat() if view.archived_at else None,
                "items": [{"name": item.name, "position": item.position} for item in view.items],
            }
        )

    def present_list(self, summaries: list[ExampleSummary]) -> str:
        return _json(
            [
                {
                    "id": str(summary.id),
                    "label": summary.label,
                    "item_count": summary.item_count,
                    "archived": summary.archived,
                }
                for summary in summaries
            ]
        )

    def present_error(self, error: Exception) -> str:
        for error_type, code, message in self._ERRORS:
            if isinstance(error, error_type):
                return _json({"code": code, "message": message})
        raise error


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)

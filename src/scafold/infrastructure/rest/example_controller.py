"""Controller REST de Example: cada rota declara o que recebe, o que devolve e os status possíveis.

Toda rota passa a ``add_api_route`` os seis argumentos do Swagger: ``summary``, ``description``,
``status_code`` (quando não é 200), ``response_model``, ``response_description`` e ``responses``,
este último tirado da tabela do presenter. A função da rota não tem ``try``/``except``: o erro sobe
e o exception handler da montagem o entrega ao presenter.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Query, status

from scafold.applications.commands.archive_example_command import ArchiveExampleCommand
from scafold.applications.commands.create_example_command import CreateExampleCommand
from scafold.applications.errors.example_not_found import ExampleNotFound
from scafold.applications.queries.example_summary import ExampleSummary
from scafold.applications.queries.example_view import ExampleView
from scafold.applications.queries.get_example_query import GetExampleQuery
from scafold.applications.queries.list_examples_query import ListExamplesQuery
from scafold.applications.shared.use_case import AsyncUnitUseCase, AsyncUseCase
from scafold.domain.bounded_context_example.errors.duplicate_item import DuplicateItem
from scafold.domain.bounded_context_example.errors.invalid_label import InvalidLabel
from scafold.domain.bounded_context_example.errors.invalid_transition import InvalidTransition
from scafold.domain.bounded_context_example.errors.label_taken import LabelTaken
from scafold.domain.bounded_context_example.value_objects.example_id import ExampleId
from scafold.infrastructure.rest.example_schemas import (
    CreateExampleRequest,
    ExampleCreatedResponse,
    ExampleListResponse,
    ExampleResponse,
)
from scafold.infrastructure.rest.mappers.example_request_mapper import ExampleRequestMapper
from scafold.infrastructure.rest.presenters.example_presenter import ExamplePresenter

#: O agrupamento das rotas no Swagger.
TAG = "examples"

#: Alias simples, e não `type`: o FastAPI precisa ver o `Annotated` para ler o `Path`.
ExampleIdPath = Annotated[
    UUID,
    Path(
        description="Identificador do Example.",
        examples=["0b6f3c52-9d0f-4d0e-8a43-5b8f6f1a2c11"],
    ),
]


class ExampleController:
    """Traduz HTTP em chamadas aos use cases; não tem regra. Os use cases chegam prontos (já
    envolvidos pelo decorator de observabilidade) e tipados pelo contrato."""

    def __init__(
        self,
        *,
        create: AsyncUseCase[CreateExampleCommand, ExampleId],
        archive: AsyncUnitUseCase[ArchiveExampleCommand],
        get: AsyncUseCase[GetExampleQuery, ExampleView],
        list_all: AsyncUseCase[ListExamplesQuery, list[ExampleSummary]],
        request_mapper: ExampleRequestMapper,
        presenter: ExamplePresenter,
    ) -> None:
        self._create = create
        self._archive = archive
        self._get = get
        self._list_all = list_all
        self._request_mapper = request_mapper
        self._presenter = presenter

        self.router = APIRouter(tags=[TAG])
        self.router.add_api_route(
            "/examples",
            self.create,
            methods=["POST"],
            summary="Cria um Example",
            description="Cria um Example com os itens informados e devolve o id gerado. "
            "A categoria é atribuída pelo serviço de classificação.",
            status_code=status.HTTP_201_CREATED,
            response_model=ExampleCreatedResponse,
            response_description="O Example foi criado.",
            responses=presenter.documented_errors(InvalidLabel, LabelTaken, DuplicateItem),
        )
        self.router.add_api_route(
            "/examples",
            self.list_all,
            methods=["GET"],
            summary="Lista Examples",
            description="Devolve os Examples por nome, com a quantidade de itens. "
            "A lista vem vazia quando não há nenhum.",
            response_model=ExampleListResponse,
            response_description="Os Examples encontrados.",
            responses=presenter.documented_errors(),
        )
        self.router.add_api_route(
            "/examples/{example_id}",
            self.get,
            methods=["GET"],
            summary="Consulta um Example",
            description="Devolve o Example do identificador informado, com os itens.",
            response_model=ExampleResponse,
            response_description="O Example encontrado.",
            responses=presenter.documented_errors(ExampleNotFound),
        )
        self.router.add_api_route(
            "/examples/{example_id}/archive",
            self.archive,
            methods=["POST"],
            summary="Arquiva um Example",
            description="Arquiva o Example do identificador informado. Arquivar é feito uma vez.",
            status_code=status.HTTP_204_NO_CONTENT,
            response_model=None,
            response_description="O Example foi arquivado.",
            responses=presenter.documented_errors(ExampleNotFound, InvalidTransition),
        )

    async def create(self, request: CreateExampleRequest) -> ExampleCreatedResponse:
        example_id = await self._create.execute(self._request_mapper.to_create_command(request))
        return self._presenter.present_created(example_id)

    async def list_all(
        self,
        # Parâmetro de query chega sempre como texto, então não há modo estrito: o tipo e a
        # restrição valem depois da conversão.
        limit: Annotated[
            int,
            Query(ge=1, le=100, description="Quantidade máxima de Examples.", examples=[20]),
        ] = 20,
    ) -> ExampleListResponse:
        summaries = await self._list_all.execute(self._request_mapper.to_list_query(limit))
        return self._presenter.present_list(summaries)

    async def get(self, example_id: ExampleIdPath) -> ExampleResponse:
        view = await self._get.execute(self._request_mapper.to_get_query(example_id))
        return self._presenter.present(view)

    async def archive(self, example_id: ExampleIdPath) -> None:
        await self._archive.execute(self._request_mapper.to_archive_command(example_id))

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from scafold.domain.bounded_context_example.aggregates.example import Example
from scafold.domain.bounded_context_example.value_objects.category import Category
from scafold.infrastructure.external.errors.unmapped_payload import UnmappedPayload
from scafold.infrastructure.external.external_category_gateway import ExternalCategoryGateway
from scafold.infrastructure.external.fake_category_api import (
    ClassifyRequestPayload,
    ClassifyResponsePayload,
    FakeCategoryApi,
)
from scafold.infrastructure.external.mappers.category_payload_mapper import (
    CategoryPayloadMapper,
)
from scafold.infrastructure.persistence.bounded_context_example.mappers.example_row_mapper import (
    ExampleRowMapper,
)
from scafold.infrastructure.persistence.bounded_context_example.sqlc import models

from ..conftest import Run
from ..support.fakes import RecordingTranslationErrorMetrics
from ..support.scene import NOW

scenarios("infrastructure/mappers.feature")


class FixedTierApi(FakeCategoryApi):
    """O fornecedor respondendo sempre o mesmo tier."""

    def __init__(self, tier: str) -> None:
        self._tier = tier

    async def classify(self, payload: ClassifyRequestPayload) -> ClassifyResponsePayload:
        return {"tier": self._tier, "confidence": "0.50"}


@pytest.fixture
def api() -> FakeCategoryApi:
    return FakeCategoryApi()


@pytest.fixture
def translation_metrics() -> RecordingTranslationErrorMetrics:
    return RecordingTranslationErrorMetrics()


@given(
    parsers.parse('um Example "{label}" da categoria "{category}" com os itens "{items}"'),
    target_fixture="example",
)
def _(label: str, category: str, items: str) -> Example:
    example = Example.create(label=label, category=Category(category), now=NOW)
    for name in items.split(", "):
        example.add_item(name)
    return example


@given(parsers.parse('o fornecedor respondendo com o tier "{tier}"'), target_fixture="api")
def _(tier: str) -> FakeCategoryApi:
    return FixedTierApi(tier)


@when("o Example vai ao formato gravado e volta", target_fixture="outcome")
def _(example: Example) -> Example:
    mapper = ExampleRowMapper()
    return mapper.to_aggregate(mapper.to_row(example), mapper.to_item_rows(example))


@when("o Example vai ao formato gravado", target_fixture="outcome")
def _(example: Example) -> models.Example:
    return ExampleRowMapper().to_row(example)


@when(parsers.parse('o fornecedor classifica "{label}"'), target_fixture="outcome")
def _(
    run: Run, api: FakeCategoryApi, translation_metrics: RecordingTranslationErrorMetrics, label: str
) -> Category | UnmappedPayload:
    gateway = ExternalCategoryGateway(
        api=api, mapper=CategoryPayloadMapper(), metrics=translation_metrics
    )
    try:
        category: Category = run(gateway.classify(label))
    except UnmappedPayload as error:
        return error
    return category


@then("o Example reconstruído é igual ao original")
def _(outcome: Example, example: Example) -> None:
    def state(value: Example) -> tuple[object, ...]:
        items = [(item.id, item.name, item.position) for item in value.items]
        return (value.id, value.label, value.category, value.created_at, value.archived_at, items)

    assert state(outcome) == state(example)


@then("o Example reconstruído nasce sem eventos")
def _(outcome: Example) -> None:
    assert outcome.get_uncommitted_events() == set()


@then(parsers.parse('o código gravado da categoria é "{code}"'))
def _(outcome: models.Example, code: str) -> None:
    assert outcome.category_code == code


@then(parsers.parse('a categoria devolvida é "{category}"'))
def _(outcome: Category | UnmappedPayload, category: str) -> None:
    assert outcome == Category(category)


@then(parsers.parse('o erro de tradução foi contado para o adaptador "{gateway}"'))
def _(translation_metrics: RecordingTranslationErrorMetrics, gateway: str) -> None:
    assert translation_metrics.failures == [gateway]

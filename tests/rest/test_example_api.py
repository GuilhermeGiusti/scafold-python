import json

from fastapi.testclient import TestClient
from httpx2 import Response
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("rest/example_api.feature")

EXAMPLES = "/api/v1/examples"


def create(client: TestClient, label: str, items: str = "") -> Response:
    item_names = [name for name in items.split(", ") if name]
    return client.post(EXAMPLES, json={"displayName": label, "itemNames": item_names})


@given(parsers.parse('o Example "{label}" criado pela API'), target_fixture="created")
def _(client: TestClient, label: str) -> Response:
    response = create(client, label)
    assert response.status_code == 201, response.text
    return response


@when(
    parsers.parse('crio pela API o Example "{label}" com os itens "{items}"'),
    target_fixture="outcome",
)
def _(client: TestClient, label: str, items: str) -> Response:
    return create(client, label, items)


@when("arquivo pela API o Example criado duas vezes", target_fixture="outcome")
def _(client: TestClient, created: Response) -> Response:
    path = f"{EXAMPLES}/{created.json()['id']}/archive"
    first = client.post(path)
    assert first.status_code == 204, first.text
    return client.post(path)


@when(parsers.parse('envio para "{method} {path}" o corpo {body}'), target_fixture="outcome")
def _(client: TestClient, method: str, path: str, body: str) -> Response:
    return client.request(method, path, json=json.loads(body))


@then(
    parsers.parse(
        'a consulta pela API do id devolvido traz o nome "{label}", '
        'a categoria "{category}" e {count:d} itens'
    )
)
def _(client: TestClient, outcome: Response, label: str, category: str, count: int) -> None:
    found = client.get(f"{EXAMPLES}/{outcome.json()['id']}").json()
    assert (found["displayName"], found["category"], len(found["items"])) == (
        label,
        category,
        count,
    )


@then(parsers.parse('a listagem traz os nomes "{names}"'))
def _(outcome: Response, names: str) -> None:
    assert [item["displayName"] for item in outcome.json()["items"]] == names.split(", ")


@then(parsers.parse('o campo recusado é "{field}"'))
def _(outcome: Response, field: str) -> None:
    assert [item["field"] for item in outcome.json()["fields"]] == [field]

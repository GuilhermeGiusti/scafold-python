from typing import Any

from httpx2 import Response
from pytest_bdd import parsers, scenarios, then

scenarios("rest/health_check.feature")


@then(parsers.parse('o corpo da resposta tem o status "{status}"'))
def _(outcome: Response, status: str) -> None:
    assert outcome.json() == {"status": status}


@then(parsers.parse('a rota documenta os status "{statuses}"'))
def _(operation: dict[str, Any], statuses: str) -> None:
    assert sorted(operation["responses"]) == statuses.split(", ")
    assert operation["summary"]
    assert operation["description"]

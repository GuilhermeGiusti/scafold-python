"""As regras que toda rota cumpre, lidas do documento OpenAPI.

Cada regra recebe o documento e o cliente HTTP e devolve as violações, uma frase por violação,
sempre começando pela rota (`POST /examples: ...`). Lista vazia é regra cumprida.
"""

from collections.abc import Callable, Iterator
from typing import Any

from fastapi.testclient import TestClient

type Document = dict[str, Any]
type Schema = dict[str, Any]
type Rule = Callable[[Document, TestClient], list[str]]

_METHODS = ("get", "post", "put", "patch", "delete")

#: O que conta como restrição em um campo de entrada, além do tipo.
_CONSTRAINTS = frozenset(
    {
        "enum",
        "const",
        "format",
        "pattern",
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "minItems",
        "maxItems",
    }
)

#: Os tipos JSON que o modo estrito protege da conversão a partir de texto.
_STRICT_TYPES = frozenset({"integer", "number", "boolean"})


def _operations(document: Document) -> Iterator[tuple[str, str, str, Schema]]:
    for path, item in document.get("paths", {}).items():
        for method in _METHODS:
            if method in item:
                yield f"{method.upper()} {path}", method, path, item[method]


def _resolve(document: Document, schema: Schema) -> Schema:
    while "$ref" in schema:
        schema = document["components"]["schemas"][schema["$ref"].rsplit("/", 1)[-1]]
    return schema


def _json_schema(document: Document, body: Schema | None) -> Schema | None:
    if body is None or "schema" not in body.get("content", {}).get("application/json", {}):
        return None
    return _resolve(document, body["content"]["application/json"]["schema"])


def _is_constrained(document: Document, schema: Schema) -> bool:
    schema = _resolve(document, schema)
    if "anyOf" in schema:
        branches = [branch for branch in schema["anyOf"] if branch.get("type") != "null"]
        return all(_is_constrained(document, branch) for branch in branches)
    if schema.get("type") in {"boolean", "object"}:
        return True
    return bool(_CONSTRAINTS & schema.keys())


def _input_fields(document: Document, operation: Schema) -> Iterator[tuple[str, Schema, Schema]]:
    """Cada campo de entrada: o nome, onde ficam descrição e exemplo, e o schema do valor."""
    for parameter in operation.get("parameters", []):
        documentation = {**parameter.get("schema", {}), **parameter}
        yield f"{parameter['in']}.{parameter['name']}", documentation, parameter.get("schema", {})
    body = _json_schema(document, operation.get("requestBody"))
    for name, schema in (body or {}).get("properties", {}).items():
        yield f"body.{name}", schema, schema


def _output_fields(document: Document, schema: Schema, prefix: str) -> Iterator[tuple[str, Schema]]:
    """Cada campo de saída, descendo em objetos e listas aninhados."""
    for name, field in _resolve(document, schema).get("properties", {}).items():
        yield f"{prefix}{name}", field
        nested = field.get("items", field)
        if "$ref" in nested:
            yield from _output_fields(document, nested, f"{prefix}{name}.")


def _success(operation: Schema) -> Iterator[tuple[str, Schema]]:
    return ((status, r) for status, r in operation.get("responses", {}).items() if status < "3")


def without_summary_or_description(document: Document, _: TestClient) -> list[str]:
    return [
        f"{route}: sem {key}"
        for route, _method, _path, operation in _operations(document)
        for key in ("summary", "description")
        if not operation.get(key)
    ]


def without_success_model(document: Document, _: TestClient) -> list[str]:
    violations = []
    for route, _method, _path, operation in _operations(document):
        bodies = [
            _json_schema(document, response)
            for status, response in _success(operation)
            if status != "204"  # 204 não tem corpo
        ]
        if any(not (body or {}).get("properties") for body in bodies) or not list(
            _success(operation)
        ):
            violations.append(f"{route}: resposta de sucesso sem modelo do corpo")
    return violations


def _has_input(operation: Schema) -> bool:
    """A rota declara parâmetro (de caminho, de query, de cabeçalho) ou corpo?"""
    return bool(operation.get("parameters")) or "requestBody" in operation


def without_validation_and_defect_errors(document: Document, _: TestClient) -> list[str]:
    """O 500 em toda rota; o 422 só na rota com entrada, porque sem entrada não há o que recusar."""
    violations: list[str] = []
    for route, _method, _path, operation in _operations(document):
        required = ("422", "500") if _has_input(operation) else ("500",)
        responses = operation.get("responses", {})
        violations.extend(
            f"{route}: {status} não documentado" for status in required if status not in responses
        )
    return violations


def with_error_outside_the_error_format(document: Document, _: TestClient) -> list[str]:
    violations = []
    for route, _method, _path, operation in _operations(document):
        for status, response in operation.get("responses", {}).items():
            if status < "4":
                continue
            body = _json_schema(document, response) or {}
            if not response.get("description"):
                violations.append(f"{route}: {status} sem descrição")
            if not {"code", "message"} <= body.get("properties", {}).keys():
                violations.append(f"{route}: {status} fora do formato de erro")
    return violations


def with_undocumented_input_field(document: Document, _: TestClient) -> list[str]:
    violations = []
    for route, _method, _path, operation in _operations(document):
        for name, documentation, schema in _input_fields(document, operation):
            if not documentation.get("description"):
                violations.append(f"{route}: {name} sem descrição")
            if not documentation.get("examples"):
                violations.append(f"{route}: {name} sem exemplo")
            if not _is_constrained(document, schema):
                violations.append(f"{route}: {name} sem restrição")
    return violations


def with_undocumented_output_field(document: Document, _: TestClient) -> list[str]:
    violations = []
    for route, _method, _path, operation in _operations(document):
        for _status, response in _success(operation):
            content = response.get("content", {}).get("application/json", {})
            for name, field in _output_fields(document, content.get("schema", {}), ""):
                if not field.get("description"):
                    violations.append(f"{route}: {name} sem descrição na saída")
                if not field.get("examples"):
                    violations.append(f"{route}: {name} sem exemplo na saída")
    return violations


def with_body_accepting_unknown_field(document: Document, _: TestClient) -> list[str]:
    violations = []
    for route, _method, _path, operation in _operations(document):
        body = _json_schema(document, operation.get("requestBody"))
        if body is not None and body.get("additionalProperties") is not False:
            violations.append(f"{route}: o corpo aceita campo desconhecido")
    return violations


def with_body_converting_text(document: Document, client: TestClient) -> list[str]:
    """O modo estrito não aparece no documento, então é provado pela resposta.

    Monta o corpo com o exemplo de cada campo e, para cada campo numérico ou booleano, envia o
    mesmo valor como texto. A rota tem de recusar apontando aquele campo.
    """
    violations = []
    for route, method, path, operation in _operations(document):
        body = _json_schema(document, operation.get("requestBody"))
        if body is None:
            continue
        properties: dict[str, Schema] = body.get("properties", {})
        if any(not field.get("examples") for field in properties.values()):
            violations.append(f"{route}: sem exemplo em todo campo, não dá para montar o corpo")
            continue
        payload = {name: field["examples"][0] for name, field in properties.items()}
        for name, field in properties.items():
            if _resolve(document, field).get("type") not in _STRICT_TYPES:
                continue
            response = client.request(method, path, json={**payload, name: str(payload[name])})
            refused = response.status_code == 422 and any(
                item.get("field") == f"body.{name}" for item in response.json().get("fields", [])
            )
            if not refused:
                violations.append(f"{route}: body.{name} aceita texto no lugar do valor")
    return violations


#: A frase do cenário para a regra que a procura.
RULES: dict[str, Rule] = {
    "rotas sem resumo ou sem descrição": without_summary_or_description,
    "rotas sem o modelo da resposta de sucesso": without_success_model,
    "rotas sem os erros de validação e de defeito": without_validation_and_defect_errors,
    "rotas com erro sem descrição ou fora do formato de erro": with_error_outside_the_error_format,
    "rotas com campo de entrada sem descrição, exemplo ou restrição": with_undocumented_input_field,
    "rotas com campo de saída sem descrição ou exemplo": with_undocumented_output_field,
    "rotas com corpo que aceita campo desconhecido": with_body_accepting_unknown_field,
    "rotas com corpo que converte texto em número": with_body_converting_text,
}

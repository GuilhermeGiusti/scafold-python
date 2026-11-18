"""A parte do presenter que é igual em toda borda REST: erro para status e corpo, e a
documentação desses erros para o Swagger (ADR-009 e ADR-011)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from scafold.applications.errors.application_error import ApplicationError
from scafold.infrastructure.rest.shared.schemas import (
    ErrorResponse,
    InvalidField,
    ValidationErrorResponse,
)


@dataclass(frozen=True, slots=True)
class ErrorEntry:
    """Um erro como o cliente o recebe, e como o Swagger o explica."""

    status: int
    code: str
    message: str
    #: Quando o erro acontece. É a descrição da resposta no Swagger.
    when: str


class ErrorPresenter:
    """A mesma tabela responde ao cliente e documenta a rota: as duas não divergem.

    O presenter de cada agregado herda daqui e declara em ``_ERRORS`` os erros dele, do mais
    específico para o mais geral, e em ``PRESENTABLE`` os erros que a montagem registra como
    exception handler. Erro de aplicação já entra pela base; erro de domínio que a borda apresenta
    entra nas duas tabelas.
    """

    #: Os erros esperados, que são resposta ao pedido. A montagem registra um handler para cada.
    PRESENTABLE: ClassVar[tuple[type[Exception], ...]] = (ApplicationError,)

    #: Os erros do agregado. Quem herda preenche.
    _ERRORS: ClassVar[tuple[tuple[type[Exception], ErrorEntry], ...]] = ()

    #: Erro de aplicação sem entrada própria em `_ERRORS`. Não é documentado nas rotas: se uma rota
    #: o devolver, o teste de comportamento documentado acusa, e falta cadastrar o erro.
    _UNLISTED: ClassVar[ErrorEntry] = ErrorEntry(
        400,
        "application_error",
        "O pedido não pôde ser atendido.",
        "O pedido foi recusado por uma regra da aplicação.",
    )

    _INVALID: ClassVar[ErrorEntry] = ErrorEntry(
        422,
        "invalid_request",
        "A entrada é inválida.",
        "Algum campo da entrada não cumpre o tipo ou a restrição documentada, "
        "ou a entrada tem um campo desconhecido.",
    )

    #: Qualquer erro fora da tabela é defeito: o cliente recebe um 500 sem detalhe interno.
    _UNEXPECTED: ClassVar[ErrorEntry] = ErrorEntry(
        500, "internal_error", "Erro interno.", "Defeito do servidor. O pedido pode ser repetido."
    )

    #: Erros levantados pelo framework, fora de qualquer rota: status para código e texto.
    _HTTP_ERRORS: ClassVar[dict[int, tuple[str, str]]] = {
        404: ("route_not_found", "Rota não encontrada."),
        405: ("method_not_allowed", "Método não aceito nesta rota."),
    }
    _HTTP_ERROR: ClassVar[tuple[str, str]] = ("http_error", "O pedido não pôde ser atendido.")

    def knows(self, error: Exception) -> bool:
        """A tabela deste presenter tem uma entrada para ``error``?

        Com mais de um agregado, a montagem entrega o erro ao presenter que o conhece.
        """
        return any(isinstance(error, error_type) for error_type, _ in self._ERRORS)

    def present_error(self, error: Exception) -> JSONResponse:
        entry = self._UNLISTED if isinstance(error, ApplicationError) else self._UNEXPECTED
        for error_type, known in self._ERRORS:
            if isinstance(error, error_type):
                entry = known
                break
        # O texto é sempre o do presenter, nunca `str(error)`: o detalhe interno não vaza.
        body = ErrorResponse(code=entry.code, message=entry.message)
        return JSONResponse(status_code=entry.status, content=body.model_dump())

    def present_validation_error(self, error: RequestValidationError) -> JSONResponse:
        """O erro de validação do framework sai no mesmo formato dos outros erros."""
        return self._invalid(sorted({self._field_path(item) for item in error.errors()}))

    def present_http_error(self, error: HTTPException) -> JSONResponse:
        """O erro que o próprio framework levanta sai no formato de erro da API.

        O 400 do framework é o corpo que ele não conseguiu ler: é entrada inválida, e sai como o 422
        documentado. Os demais (rota inexistente, método não aceito) mantêm o status.
        """
        if error.status_code == 400:
            return self._invalid(["body"])
        code, message = self._HTTP_ERRORS.get(error.status_code, self._HTTP_ERROR)
        content = ErrorResponse(code=code, message=message).model_dump()
        return JSONResponse(status_code=error.status_code, content=content, headers=error.headers)

    @classmethod
    def documented_errors(
        cls, *errors: type[Exception], validation: bool = True
    ) -> dict[int | str, dict[str, Any]]:
        """O valor de ``responses=`` de uma rota: os erros que ela pode devolver.

        O 500 entra em toda rota. O 422 entra em toda rota com entrada (parâmetro de caminho, de
        query ou corpo); a rota sem entrada passa ``validation=False``. Os demais são os que o use
        case da rota levanta. Dois erros com o mesmo status juntam as descrições.
        """
        by_type = dict(cls._ERRORS)
        documented: dict[int | str, dict[str, Any]] = {}
        for error in errors:
            # `KeyError` aqui é de propósito: a rota não documenta um erro que o presenter não
            # sabe apresentar, e a montagem do app falha.
            entry = by_type[error]
            previous = documented.get(entry.status)
            description = entry.when if previous is None else f"{previous['description']} Ou: {entry.when}"
            documented[entry.status] = {"model": ErrorResponse, "description": description}
        if validation:
            documented[cls._INVALID.status] = {
                "model": ValidationErrorResponse,
                "description": cls._INVALID.when,
            }
        documented[cls._UNEXPECTED.status] = {
            "model": ErrorResponse,
            "description": cls._UNEXPECTED.when,
        }
        return documented

    def _invalid(self, fields: list[str]) -> JSONResponse:
        body = ValidationErrorResponse(
            code=self._INVALID.code,
            message=self._INVALID.message,
            fields=[InvalidField(field=field) for field in fields],
        )
        return JSONResponse(status_code=self._INVALID.status, content=body.model_dump())

    @staticmethod
    def _field_path(item: Any) -> str:
        # No JSON malformado o framework põe a posição do caractere no caminho. O cliente só precisa
        # saber que o problema é o corpo.
        parts = item["loc"][:1] if item["type"] == "json_invalid" else item["loc"]
        return ".".join(str(part) for part in parts)

"""Log estruturado: uma linha JSON por registro, com campos fixos e o id do trace.

**O id do trace é o identificador de correlação.** Toda linha escrita enquanto uma request é
atendida leva o ``trace_id`` do span corrente. Não existe um identificador de correlação à parte.

**A mensagem da exceção nunca é escrita.** Erro de domínio costuma citar o dado recusado, e erro de
driver traz o SQL com os parâmetros. Da exceção saem o nome da classe e a pilha de chamadas, que só
tem código: arquivo, linha e função.

**O nível vem da configuração.** Por padrão, só WARNING e ERROR aparecem; com ``LOG_DEBUG=true``,
tudo aparece. O nível vale para o projeto e para as bibliotecas de terceiros, porque é aplicado no
logger raiz.
"""

from __future__ import annotations

import json
import logging
import sys
import traceback
from datetime import UTC, datetime
from typing import TextIO

from opentelemetry import trace

#: Os campos que toda linha tem, nesta ordem. `trace_id` e `span_id` são nulos fora de um span.
LOG_FIELDS = ("timestamp", "level", "logger", "message", "service", "trace_id", "span_id")

#: Os campos a mais de uma linha que registra uma exceção.
ERROR_FIELDS = ("error_type", "stack")


class JsonLogFormatter(logging.Formatter):
    """Formata cada registro como uma linha JSON.

    O id do trace é lido do span corrente na hora de formatar: o handler precisa formatar no mesmo
    fluxo que escreveu o registro.
    """

    def __init__(self, *, service: str) -> None:
        super().__init__()
        self._service = service

    def format(self, record: logging.LogRecord) -> str:
        context = trace.get_current_span().get_span_context()
        entry: dict[str, str | None] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self._service,
            "trace_id": trace.format_trace_id(context.trace_id) if context.is_valid else None,
            "span_id": trace.format_span_id(context.span_id) if context.is_valid else None,
        }
        if record.exc_info is not None and record.exc_info[0] is not None:
            error_class, _, stack = record.exc_info
            entry["error_type"] = error_class.__name__
            entry["stack"] = "".join(traceback.format_tb(stack))
        return json.dumps(entry, ensure_ascii=False)


def configure_logging(
    *, service: str, level: int, stream: TextIO = sys.stdout
) -> logging.Handler:
    """Põe o formatador JSON no logger raiz, no lugar do que houver. Uma vez, na montagem."""
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonLogFormatter(service=service))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    return handler

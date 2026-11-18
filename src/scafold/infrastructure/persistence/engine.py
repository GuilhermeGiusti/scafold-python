"""O engine do banco: um por processo, a partir de ``DATABASE_URL``.

A URL do contrato é ``postgresql://``, sem driver. O ``+asyncpg`` que o SQLAlchemy exige é detalhe
deste adaptador e entra só aqui. O mesmo vale para ``sslmode``, que o asyncpg só aceita como
argumento de conexão, com o nome ``ssl``.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

#: O esquema aceito em `DATABASE_URL`.
ACCEPTED_SCHEME = "postgresql"

#: O esquema que o SQLAlchemy exige para escolher o driver assíncrono.
_DRIVER_SCHEME = "postgresql+asyncpg"


class InvalidDatabaseUrl(ValueError):
    """``DATABASE_URL`` com esquema diferente de ``postgresql://``."""


def connect_arguments(database_url: str) -> tuple[str, dict[str, Any]]:
    """Traduz a URL do contrato para a do driver. Função pura, testável sem conexão."""
    parts = urlsplit(database_url)
    if parts.scheme != ACCEPTED_SCHEME:
        raise InvalidDatabaseUrl(f"DATABASE_URL deve usar o esquema {ACCEPTED_SCHEME}://")
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    arguments: dict[str, Any] = {}
    sslmode = query.pop("sslmode", None)
    if sslmode is not None:
        arguments["ssl"] = sslmode
    url = urlunsplit((_DRIVER_SCHEME, parts.netloc, parts.path, urlencode(query), parts.fragment))
    return url, arguments


def open_engine(database_url: str) -> AsyncEngine:
    """O engine do processo. Criar não conecta: o pool abre a primeira conexão no primeiro uso."""
    url, arguments = connect_arguments(database_url)
    return create_async_engine(url, connect_args=arguments)

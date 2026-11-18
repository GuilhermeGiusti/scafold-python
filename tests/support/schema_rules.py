"""As regras de schema e de acesso a dados, como funções que devolvem as violações encontradas.

Ficam separadas dos testes para que cada regra seja provada duas vezes: contra os arquivos reais (não
há violação) e contra um exemplo errado (a violação é encontrada). Um portão que nunca reprova
nada não prova nada.
"""

from __future__ import annotations

import ast
import re

#: Objetos que fazem o banco AGIR. O schema só recusa: restrição, chave estrangeira e CHECK.
_FORBIDDEN_OBJECTS = re.compile(
    r"\bCREATE\s+(?:OR\s+REPLACE\s+)?(?:CONSTRAINT\s+)?(TRIGGER|FUNCTION|PROCEDURE|RULE)\b",
    re.IGNORECASE,
)

#: DEFAULT de instante: o instante vem do relógio injetado no use case, nunca do banco.
_INSTANT_DEFAULT = re.compile(
    r"\bDEFAULT\s+(now\s*\(|CURRENT_TIMESTAMP|CURRENT_DATE|LOCALTIMESTAMP|clock_timestamp\s*\(|"
    r"statement_timestamp\s*\(|transaction_timestamp\s*\()",
    re.IGNORECASE,
)

#: Palavra-chave de restrição -> prefixo obrigatório do nome.
_PREFIXES = {
    "PRIMARY KEY": "pk_",
    "FOREIGN KEY": "fk_",
    "UNIQUE": "uq_",
    "CHECK": "ck_",
}
_CONSTRAINT_KEYWORD = re.compile(r"\b(PRIMARY\s+KEY|FOREIGN\s+KEY|REFERENCES|UNIQUE|CHECK)\b", re.I)
_NAMED = re.compile(r"^\s*CONSTRAINT\s+(\w+)\s+(PRIMARY\s+KEY|FOREIGN\s+KEY|UNIQUE|CHECK)\b", re.I)
_CREATE_TABLE = re.compile(r"\bCREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\s*\(", re.IGNORECASE)
_ALTER_ADD = re.compile(
    r"\bALTER\s+TABLE\s+(?:ONLY\s+)?(\w+)\s+ADD\s+(?!COLUMN\b)(.*?);", re.IGNORECASE | re.DOTALL
)
_UNNAMED_INDEX = re.compile(r"\bCREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:CONCURRENTLY\s+)?ON\b", re.I)

#: Módulos do ORM do SQLAlchemy. O acesso é SQL-first: só o Core, pelo código gerado.
_ORM_MODULES = ("sqlalchemy.orm", "sqlalchemy.ext.declarative", "sqlalchemy.ext.automap")
_ORM_NAMES = {"AsyncSession", "async_sessionmaker", "async_scoped_session"}


def strip_sql_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    return re.sub(r"--[^\n]*", " ", sql)


def forbidden_objects(sql: str) -> list[str]:
    """Triggers, functions, procedures e rules criados pela migration."""
    return [match.group(0) for match in _FORBIDDEN_OBJECTS.finditer(strip_sql_comments(sql))]


def instant_defaults(sql: str) -> list[str]:
    """DEFAULTs que leem o relógio do banco."""
    return [match.group(0) for match in _INSTANT_DEFAULT.finditer(strip_sql_comments(sql))]


def unnamed_constraints(sql: str) -> list[str]:
    """Restrições sem `CONSTRAINT <nome>`, com o prefixo errado, ou índices sem nome."""
    clean = strip_sql_comments(sql)
    problems: list[str] = []
    for match in _CREATE_TABLE.finditer(clean):
        table = match.group(1)
        for item in _top_level_items(_body(clean, match.end() - 1)):
            problems.extend(_check_item(table, item))
    for match in _ALTER_ADD.finditer(clean):
        problems.extend(_check_item(match.group(1), match.group(2)))
    problems.extend(f"indice sem nome: {m.group(0)}" for m in _UNNAMED_INDEX.finditer(clean))
    return problems


def orm_imports(source: str, filename: str = "<python>") -> list[str]:
    """Imports do ORM do SQLAlchemy num módulo Python."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source, filename=filename)):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names if alias.name.startswith(_ORM_MODULES))
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            if node.module.startswith(_ORM_MODULES):
                found.append(node.module)
            elif node.module.startswith("sqlalchemy"):
                found.extend(
                    f"{node.module}.{alias.name}" for alias in node.names if alias.name in _ORM_NAMES
                )
    return found


def _body(sql: str, open_paren: int) -> str:
    """O conteúdo entre o parêntese de `CREATE TABLE x (` e o que o fecha."""
    depth = 0
    for index in range(open_paren, len(sql)):
        if sql[index] == "(":
            depth += 1
        elif sql[index] == ")":
            depth -= 1
            if depth == 0:
                return sql[open_paren + 1 : index]
    raise ValueError("CREATE TABLE sem parentese de fechamento")


def _top_level_items(body: str) -> list[str]:
    """Colunas e restrições, separadas pelas vírgulas fora de parênteses."""
    items: list[str] = []
    current: list[str] = []
    depth = 0
    for char in body:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if char == "," and depth == 0:
            items.append("".join(current))
            current = []
        else:
            current.append(char)
    items.append("".join(current))
    return [item.strip() for item in items if item.strip()]


def _check_item(table: str, item: str) -> list[str]:
    if not _CONSTRAINT_KEYWORD.search(item):
        return []
    named = _NAMED.match(item)
    if named is None:
        return [f"{table}: restricao sem nome: {' '.join(item.split())}"]
    name, keyword = named.group(1), " ".join(named.group(2).upper().split())
    prefix = _PREFIXES[keyword]
    if not name.startswith(prefix):
        return [f"{table}: {keyword} {name!r} deveria comecar com {prefix!r}"]
    return []

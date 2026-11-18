---
title: Migrations e queries SQL
version: 1.0.0
---

# Migrations e queries SQL

## Propósito

Depois de ler, você saberá escrever o SQL-fonte de um bounded context: a migration que cria ou altera tabelas, aplicada pelo Flyway, e o arquivo de queries que o sqlc transforma em código Python. Saberá também aplicar as migrations na stack local e nos testes. A referência é [`migrations/`](../scafold/migrations/) e [`queries/`](../scafold/queries/).

## Problema que resolve

Sem um padrão, cada contexto escreve SQL de um jeito: query como string num `.py` fica fora da geração e das validações, uma versão sequencial colide entre dois PRs abertos ao mesmo tempo, e uma restrição sem nome não pode ser traduzida em erro de domínio, porque o nome gerado pelo Postgres não é contrato de ninguém.

## Por que foi criado

Pedido de 2026-11-18: guidances que ensinem a implementar seguindo o projeto de referência `../scafold`, para usar em outros repositórios. A decisão que o sustenta é a ADR-003 (PostgreSQL, Flyway e acesso SQL-first com sqlc).

## Como implementar

### 1. Onde o SQL mora

Fora do pacote Python, numa pasta por bounded context:

```text
migrations/<contexto>/V<AAAAMMDDHHMMSS>__<descricao>.sql   # schema, aplicado pelo Flyway
queries/<contexto>/<agregado>_write.sql                  # escritas, dentro da Unit of Work
queries/<contexto>/<agregado>_read.sql                   # leituras, dentro ou fora dela
```

Na referência: [`V20261118120000__example.sql`](../scafold/migrations/example/V20261118120000__example.sql), [`example_write.sql`](../scafold/queries/example/example_write.sql) e [`example_read.sql`](../scafold/queries/example/example_read.sql). A outbox, contexto técnico, segue o mesmo formato em `migrations/outbox/` e `queries/outbox/`.

### 2. Escrever a migration

A versão é o instante de criação em UTC, com segundos. O Flyway numera as versões globalmente entre as pastas, e o timestamp evita colisão entre PRs paralelos.

O schema só recusa dados: restrição, chave estrangeira e `CHECK`. Nada de trigger, function, rule nem `DEFAULT` de instante, porque o instante vem do relógio injetado no use case. **Toda** restrição tem nome `<prefixo>_<tabela>_<coluna(s)>`, com `pk_`, `fk_`, `uq_` e `ck_`; índice também tem nome. Veja as restrições de `example` e `example_item`, como `uq_example_label` e `ck_example_category_code`.

A outbox registra uma exceção da ADR-006: o relógio dela é o do banco, preenchido com `now()` explicitamente nas queries, e o id tem `DEFAULT gen_random_uuid()`. Veja [`V20261118120100__outbox.sql`](../scafold/migrations/outbox/V20261118120100__outbox.sql).

Migration aplicada não se edita: a mudança vira arquivo novo, com timestamp novo, e o código gerado é regerado.

### 3. Escrever as queries

Cada query começa com `-- name: <NomeEmPascalCase> :<tipo>`. Os parâmetros usam `sqlc.arg(<nome>)`, e `sqlc.narg(<nome>)` para o que aceita nulo. Os tipos usados na referência:

| Tipo | O que o método gerado devolve | Exemplo |
|---|---|---|
| `:exec` | nada | `InsertExample`, `UpdateExampleArchivedAt` |
| `:execrows` | quantas linhas a query afetou | `DeleteArchivedExamples` |
| `:one` | uma linha ou `None` | `GetExample`, `InsertOutboxMessage` (com `RETURNING`) |
| `:many` | um iterador assíncrono | `ListExampleItems`, `ListExampleSummaries` |

O nome vai para o código em snake_case (`InsertExample` vira `insert_example`) e é o rótulo `query` de `db_query_duration_seconds`. Não use `:copyfrom` nem `:batch*`: o plugin não os gera, e `make sqlc-check` reprova a anotação.

### 4. Aplicar na stack local

O Flyway roda como job do [`docker-compose.yml`](../scafold/docker-compose.yml), no serviço `flyway`, com uma location por contexto em `FLYWAY_LOCATIONS`, um volume somente leitura por pasta e `FLYWAY_CLEAN_DISABLED: "true"`. Um contexto novo acrescenta a location e o volume.

| Alvo do [`Makefile`](../scafold/Makefile) | O que faz |
|---|---|
| `make stack-up` | sobe o Postgres e o resto da stack; `POSTGRES_PORT=55432` se a 5432 estiver ocupada |
| `make migrate-up` | roda `flyway migrate` como job (`run --rm`) |
| `make migrate-info` | mostra o que foi aplicado e o que está pendente |

### 5. Aplicar nos testes

Os testes de integração aplicam as migrations com o **mesmo** Flyway, num container ligado ao Postgres do testcontainers por uma rede própria. As pastas entram no dicionário `FLYWAY_LOCATIONS` de [`tests/conftest.py`](../scafold/tests/conftest.py); `_run_flyway` falha o setup se o Flyway falhar, e a fixture `database_url` esvazia as tabelas a cada cenário, exceto `flyway_schema_history`.

### 6. Os portões

Um teste lê cada migration e reprova o que quebra as regras, sem Docker. As regras estão em [`tests/support/schema_rules.py`](../scafold/tests/support/schema_rules.py) (`forbidden_objects`, `instant_defaults`, `unnamed_constraints`), e cada uma é provada contra as migrations reais e contra um exemplo errado, em [`schema_and_orm.feature`](../scafold/tests/features/architecture/schema_and_orm.feature).

## Guidances relacionados

- [Geração de código com sqlc](geracao-de-codigo-com-sqlc.md) (v1.0.0): como este SQL vira código e quais portões o validam.
- [Repositório e leitor sobre o querier do sqlc](repositorio-e-leitor-sobre-sqlc.md) (v1.0.0): como o repositório chama as queries e traduz as restrições nomeadas.
- [Portões de arquitetura](portoes-de-arquitetura.md) (v1.0.0): os testes que cobram as regras do schema.

## Change log

| Versão | Data       | Pessoa           | Motivo                                                                                   |
|--------|------------|------------------|------------------------------------------------------------------------------------------|
| 1.0.0  | 2026-11-18 | Guilherme Giusti | Criação: ensinar a escrever migrations e queries com o scaffold como referência          |

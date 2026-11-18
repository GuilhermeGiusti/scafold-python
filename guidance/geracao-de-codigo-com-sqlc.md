---
title: Geração de código com sqlc
version: 1.0.0
---

# Geração de código com sqlc

## Propósito

Depois de ler, você saberá configurar o sqlc para um bounded context, gerar o código Python de acesso a dados com `make generate` e usar os portões `make sqlc-check` e `make sqlc-vet`. A referência é o [`sqlc.yaml`](../scafold/sqlc.yaml) e o [`Makefile`](../scafold/Makefile).

## Problema que resolve

Sem a geração, cada repositório escreveria SQL à mão, sem tipo e sem validação contra o schema. Com ela, o código gerado pode ficar para trás do SQL ou carregar uma query que o Postgres recusa: os dois portões existem para isso. E duas máquinas com versões diferentes do sqlc gerariam código diferente.

## Por que foi criado

Pedido de 2026-11-18: guidances que ensinem a implementar seguindo o projeto de referência `../scafold`, para usar em outros repositórios. A decisão que o sustenta é a ADR-003 (PostgreSQL, Flyway e acesso SQL-first com sqlc).

## Como implementar

### 1. Um bloco do `sqlc.yaml` por bounded context

Cada contexto tem um bloco que enxerga só as próprias migrations e queries, então um JOIN que cruze a fronteira nem chega a gerar código. O plugin é o WASM `sqlc-gen-python`, com versão e sha256 fixados. O bloco do contexto `example` aponta `schema` para `migrations/example` e `queries` para `queries/example`, liga a regra `sqlc/db-prepare`, lê a URI de `SQLC_DATABASE_URI` e declara `analyzer.database: false`, para `generate` e `diff` não falarem com o banco. A outbox tem o seu bloco, como contexto técnico.

Um contexto novo ganha um bloco copiado, trocando `schema`, `queries`, `out` e `package`:

- `package` é o caminho **completo** do pacote gerado; sem ele, o código importa `from sqlc import models`, que não existe.
- `out` fica em `infrastructure/persistence/<contexto>/sqlc`, junto do repositório que o usa. O domínio nunca importa nada dali.
- O plugin não cria `__init__.py`: crie um vazio na pasta `sqlc/` na primeira geração.
- `emit_async_querier: true` gera `AsyncQuerier` sobre a `AsyncConnection` do SQLAlchemy Core. O ORM não entra.

### 2. Gerar o código

`make generate` confere a versão fixada em `SQLC_VERSION` (pela macro `assert_sqlc_version`) e gera. O código gerado é **commitado** e **nunca editado à mão**: mude o SQL, rode `make generate` e commite o SQL e a pasta `sqlc/` juntos. Exemplos do resultado: [`sqlc/example_write.py`](../scafold/src/scafold/infrastructure/persistence/bounded_context_example/sqlc/example_write.py), com `InsertExampleParams` e `AsyncQuerier`, e [`sqlc/example_read.py`](../scafold/src/scafold/infrastructure/persistence/bounded_context_example/sqlc/example_read.py). Uma query com muitos parâmetros recebe um objeto `...Params`; com poucos, argumentos nomeados.

O comentário `-- name: insert_example` continua no SQL que vai ao banco, e é dele que o ouvinte de métricas tira o rótulo `query`.

### 3. O portão `sqlc-check`

`make sqlc-check` roda `sqlc diff` e falha se o código commitado não corresponder ao SQL, e reprova as anotações que o plugin não gera (`:copyfrom` e `:batch*`), apontando arquivo e linha, pela macro `assert_no_unsupported_annotations`. Não precisa de banco.

### 4. O portão `sqlc-vet`

`make sqlc-vet` roda `sqlc vet` com `sqlc/db-prepare`, que prepara cada query contra um Postgres real; exige `make stack-up migrate-up`. O `generate` lê o schema das migrations e recusa coluna inexistente; o `vet` pega o que só o Postgres recusa, como operador inexistente para os tipos.

### 5. O portão que proíbe o ORM

Um teste percorre todo `.py` de `src/` e `tests/` e reprova import do ORM, lendo a árvore sintática. A regra é `orm_imports`, em [`tests/support/schema_rules.py`](../scafold/tests/support/schema_rules.py), provada em [`schema_and_orm.feature`](../scafold/tests/features/architecture/schema_and_orm.feature).

### 6. Os alvos

| Alvo | O que faz |
|---|---|
| `make generate` | regera o código; commite junto com o SQL |
| `make sqlc-check` | confere que o código está em dia e sem anotação não suportada (sem Docker) |
| `make sqlc-vet` | prepara cada query contra o Postgres (exige a stack migrada) |
| `make check` | `typecheck`, `sqlc-check`, `sqlc-vet` e `test` |

O Makefile usa `bash`. Sem GNU make, rode o comando da receita direto, como `SQLC_DATABASE_URI=... sqlc diff`.

## Guidances relacionados

- [Migrations e queries SQL](migrations-e-queries-sql.md) (v1.0.0): como escrever o SQL que o sqlc lê.
- [Repositório e leitor sobre o querier do sqlc](repositorio-e-leitor-sobre-sqlc.md) (v1.0.0): como o repositório usa o `AsyncQuerier`.
- [Unit of Work com métricas](unit-of-work-com-metricas.md) (v1.0.0): como o nome da query vira rótulo.

## Change log

| Versão | Data       | Pessoa           | Motivo                                                                                   |
|--------|------------|------------------|------------------------------------------------------------------------------------------|
| 1.0.0  | 2026-11-18 | Guilherme Giusti | Criação: ensinar a configurar e gerar o código com sqlc com o scaffold como referência   |

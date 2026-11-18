---
title: Repositório e leitor sobre o querier do sqlc
version: 1.0.0
---

# Repositório e leitor sobre o querier do sqlc

## Propósito

Depois de ler, você saberá escrever o acesso a dados de um agregado: a porta do repositório no domínio, a implementação SQL na infraestrutura com o mapper de persistência, e o leitor dedicado, que devolve DTO sem reconstruir o agregado. Verá também como o fake e a implementação SQL passam pelo mesmo teste de contrato. A referência é `SqlExampleRepository` e `SqlExampleReader`, em [`infrastructure/persistence/bounded_context_example/`](../scafold/src/scafold/infrastructure/persistence/bounded_context_example/).

## Problema que resolve

No repositório, a forma da referência garante quatro coisas: ele nunca decide sobre a transação; uma escrita fora da transação é recusada, em vez de se perder em silêncio; toda query que ele executa leva o nome dele na métrica; e a regra de unicidade fica com o banco, porque duas criações simultâneas passariam as duas por uma consulta anterior.

## Por que foi criado

Pedido de 2026-11-18: guidances que ensinem a implementar seguindo o projeto de referência `../scafold`, para usar em outros repositórios. As decisões que o sustentam são a ADR-003 (PostgreSQL, Flyway e acesso SQL-first com sqlc), a ADR-004 (Unit of Work com transação nomeada, repositórios e leitores) e a ADR-009 (Mappers e presenters nas periferias do domínio).

## Como implementar

### 1. A porta fica no domínio

Um `Protocol` em `domain/<contexto>/repositories/<agregado>_repository.py`, que fala só de agregado, id e erro de domínio. Veja `IExampleRepository`, em [`example_repository.py`](../scafold/src/scafold/domain/bounded_context_example/repositories/example_repository.py): `add` (levanta `LabelTaken`), `get` (devolve `None` quando não existe), `save` e `remove_archived`.

### 2. O mapper de persistência

As linhas geradas pelo sqlc não saem do repositório: o `ExampleRowMapper`, em [`mappers/example_row_mapper.py`](../scafold/src/scafold/infrastructure/persistence/bounded_context_example/mappers/example_row_mapper.py), traduz nas duas direções (`to_row`, `to_item_rows`, `to_aggregate`). O detalhe de armazenamento fica nele: a categoria gravada como código de uma letra, nas tabelas `_CODE_BY_CATEGORY` e `_CATEGORY_BY_CODE`. `to_aggregate` reconstrói pelo construtor.

### 3. A implementação fica na infraestrutura

Em `infrastructure/persistence/<contexto>/sql_<agregado>_repository.py`, ao lado da pasta `sqlc/` gerada. Recebe a `UnitOfWork` concreta e o mapper, e declara duas constantes: `REPOSITORY_NAME` (o nome da porta sem o `I`, em snake_case, rótulo em `db_query_duration_seconds`) e `LABEL_UNIQUE_CONSTRAINT` (a restrição que vira `LabelTaken`). Veja [`sql_example_repository.py`](../scafold/src/scafold/infrastructure/persistence/bounded_context_example/sql_example_repository.py).

### 4. Gravar pelo `write_querier`

O repositório nunca abre, commita nem reverte. Para escrever, pede `write_querier(REPOSITORY_NAME)`, cria o `AsyncQuerier` gerado sobre a conexão e chama as queries. Veja `SqlExampleRepository.add` (a raiz e os itens na mesma transação), `save` e `remove_archived` (`:execrows`, que devolve quantas linhas saíram). Gravar pelo `querier(...)` é o que não fazer: fora de transação, a gravação é revertida na devolução ao pool.

### 5. Traduzir a restrição pelo nome

O repositório traduz só a violação de `uq_example_label` em `LabelTaken`; qualquer outra violação sobe como está, porque indica defeito. O nome vem da exceção do asyncpg embrulhada pelo SQLAlchemy, lida por `_violated_constraint`, e nunca da mensagem do driver. Como o erro sobe de dentro do bloco, a transação é revertida e medida como `rolled_back`, com `error_type="LabelTaken"`.

### 6. Ler e reconstruir o agregado

Quando a query precisa do agregado inteiro, a leitura é do repositório, pelo `querier(REPOSITORY_NAME)`. O `:many` é um iterador assíncrono e é consumido **dentro** do `async with`, porque a conexão volta ao pool na saída. Veja `SqlExampleRepository.get`.

### 7. Ler sem o agregado: o leitor dedicado

Quando a query só mostra dados, ela usa um leitor que devolve DTO pronto. A porta fica em `applications/ports/` e o DTO em `applications/queries/`: `IExampleReader`, em [`example_reader.py`](../scafold/src/scafold/applications/ports/example_reader.py), e `ExampleSummary`. A implementação fica ao lado do repositório, com `READER_NAME`, e só lê: veja `SqlExampleReader`, em [`sql_example_reader.py`](../scafold/src/scafold/infrastructure/persistence/bounded_context_example/sql_example_reader.py). A query faz o trabalho que o agregado faria em memória, como o `count` com `LEFT JOIN` de `ListExampleSummaries`.

### 8. Testar com teste de contrato

Cada porta tem um fake em memória e um adaptador SQL, e os dois passam pelos mesmos cenários. Os fakes de [`tests/support/fakes.py`](../scafold/tests/support/fakes.py) formam um par coerente sobre um único store: a `FakeUnitOfWork` desfaz, quando o bloco levanta, o que o `InMemoryExampleRepository` gravou, e o repositório em memória recusa gravar fora da transação. A fixture `backend`, em [`tests/conftest.py`](../scafold/tests/conftest.py), entrega uma implementação completa de cada lado; o lado `postgres` leva a marca `integration`. O contrato está em [`example_repository_contract.feature`](../scafold/tests/features/infrastructure/example_repository_contract.feature), e o mapper tem o seu cenário de ida e volta em [`mappers.feature`](../scafold/tests/features/infrastructure/mappers.feature).

## Guidances relacionados

- [Unit of Work com métricas](unit-of-work-com-metricas.md) (v1.0.0): como `write_querier` e `querier` recusam e rotulam.
- [Migrations e queries SQL](migrations-e-queries-sql.md) (v1.0.0): onde a restrição `uq_example_label` é declarada.
- [Geração de código com sqlc](geracao-de-codigo-com-sqlc.md) (v1.0.0): de onde vêm `example_write.AsyncQuerier` e `example_read.AsyncQuerier`.
- [Mappers e presenters](mappers-e-presenters.md) (v1.0.0): as regras comuns a todo mapper.
- [Testes de contrato e de integração com BDD](testes-de-contrato-e-integracao-com-bdd.md) (v1.0.0): como o mesmo cenário roda contra o fake e contra o banco.

## Change log

| Versão | Data       | Pessoa           | Motivo                                                                                   |
|--------|------------|------------------|------------------------------------------------------------------------------------------|
| 1.0.0  | 2026-11-18 | Guilherme Giusti | Criação: ensinar a escrever repositório e leitor sobre o código do sqlc com o scaffold como referência |

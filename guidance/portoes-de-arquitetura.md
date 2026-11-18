---
title: Portões de arquitetura
version: 1.0.0
---

# Portões de arquitetura

## Propósito

Depois de ler, você saberá escrever um teste que cobra uma regra de estrutura do código sem depender de review: os imports permitidos em cada camada, quem pode ler o ambiente, o ORM proibido, as regras do schema e o argumento `telemetry` em todo app. Saberá também provar que o portão funciona. A referência é [`tests/architecture/`](../scafold/tests/architecture/), [`tests/support/schema_rules.py`](../scafold/tests/support/schema_rules.py) e [`tests/rest/test_framework_telemetry.py`](../scafold/tests/rest/test_framework_telemetry.py).

## Problema que resolve

Uma regra que só existe em documento ou em review é quebrada no primeiro PR apressado: o domínio importa o framework, alguém lê `os.environ` no meio do código, uma migration ganha um `DEFAULT now()`. E um portão que nunca reprova nada não prova nada: ele pode estar quebrado e passar sempre.

## Por que foi criado

Pedido de 2026-11-18: guidances que ensinem a implementar seguindo o projeto de referência `../scafold`, para usar em outros repositórios. As regras cobradas vêm da ADR-002 (Domain Driven Design nos módulos backend), da ADR-003 (PostgreSQL, Flyway e acesso SQL-first com sqlc) e da ADR-012 (Observabilidade dos módulos de backend com OpenTelemetry); este guidance só ensina a cobrá-las.

## Como implementar

### 1. Leia o código pela árvore sintática

Os portões leem os arquivos com `ast`, e não com busca de texto: um módulo citado numa string ou num comentário não conta. Veja `imported_modules` e `environment_reads`, em [`test_boundaries.py`](../scafold/tests/architecture/test_boundaries.py), e `orm_imports`, em [`schema_rules.py`](../scafold/tests/support/schema_rules.py). O SQL é lido com os comentários removidos antes (`strip_sql_comments`).

### 2. Cada regra devolve as violações

A regra é uma função que recebe o código (ou o SQL) e devolve a lista do que achou, vazia quando a regra é cumprida. Assim a mesma função serve ao código real e ao exemplo errado, e a mensagem do teste lista o que quebrou.

### 3. Prove cada regra duas vezes

Um cenário aplica a regra ao código real e exige que nada seja encontrado; outro a aplica a um exemplo errado e exige que a violação seja encontrada. Veja [`boundaries.feature`](../scafold/tests/features/architecture/boundaries.feature) e [`schema_and_orm.feature`](../scafold/tests/features/architecture/schema_and_orm.feature). Uma regra nova ganha as duas linhas.

### 4. Os portões da referência

| Portão | Regra | Onde |
|---|---|---|
| Camadas | `domain` não importa aplicação, infraestrutura, montagem nem biblioteca de borda, banco, telemetria ou broker; `applications` não importa infraestrutura, montagem nem essas bibliotecas | `boundaries.feature`, com a lista de prefixos proibidos nos `Exemplos` |
| Ambiente | nenhum módulo de `src/` lê `os.environ` nem `os.getenv`; só `entrypoint/` lê | `boundaries.feature` |
| ORM | nenhum `.py` de `src/` e `tests/` importa `sqlalchemy.orm`, `AsyncSession` e afins | `schema_and_orm.feature`, regra `orm_imports` |
| Schema | migration não cria trigger, function, procedure nem rule (`forbidden_objects`), não tem `DEFAULT` de instante (`instant_defaults`) e toda restrição e índice têm nome com o prefixo do tipo (`unnamed_constraints`) | `schema_and_orm.feature` |
| Telemetria do framework | toda chamada `FastAPI(...)` em `src/` e `entrypoint/` passa o argumento `telemetry` | [`framework_telemetry.feature`](../scafold/tests/features/rest/framework_telemetry.feature) |
| Documentação da API | as 8 regras sobre o OpenAPI e o Schemathesis | [API REST documentada e validada](api-rest-documentada-e-validada.md) |
| Código gerado | o código do sqlc corresponde ao SQL | `make sqlc-check` (veja [Geração de código com sqlc](geracao-de-codigo-com-sqlc.md)) |

Todos rodam sem Docker, em `uv run pytest -m "not integration"`, e entram em `make check`.

### 5. Um portão novo

Escreva a regra como função que devolve violações, num módulo de `tests/support/` (ou no próprio módulo de teste, se só ele a usa), o cenário contra o código real e o cenário contra o exemplo errado. Uma camada nova, ou uma biblioteca que não pode cruzar uma fronteira, entra como linha nova nos `Exemplos` de `boundaries.feature`.

## Guidances relacionados

- [Pacotes e camadas de um módulo](pacotes-e-camadas-do-modulo.md) (v1.0.0): as camadas que o portão de imports cobra.
- [Migrations e queries SQL](migrations-e-queries-sql.md) (v1.0.0): as regras do schema.
- [Configuração pelo ambiente e nível do log](configuracao-pelo-ambiente.md) (v1.0.0): por que só a configuração lê o ambiente.
- [Testes com BDD e arquivos .feature](testes-com-bdd.md) (v1.0.0): como escrever os cenários.

## Change log

| Versão | Data       | Pessoa           | Motivo                                                                                   |
|--------|------------|------------------|------------------------------------------------------------------------------------------|
| 1.0.0  | 2026-11-18 | Guilherme Giusti | Criação: ensinar a cobrar regras de estrutura por teste com o scaffold como referência    |

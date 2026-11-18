---
title: Testes de contrato e de integração com BDD
version: 1.0.0
---

# Testes de contrato e de integração com BDD

## Propósito

Depois de ler, você saberá escrever dois tipos de teste que partem de um `.feature` e usam infraestrutura real: o teste de contrato, que roda o mesmo cenário contra o fake de uma porta e contra o adaptador real, e o teste de integração, que prova o que só o banco ou o broker real podem provar. Saberá subir Postgres (migrado pelo Flyway) e RabbitMQ em container com `testcontainers` e separar o que roda sem Docker do que exige Docker. A referência é [`tests/conftest.py`](../scafold/tests/conftest.py) e [`tests/infrastructure/`](../scafold/tests/infrastructure/).

## Problema que resolve

Um fake só é útil se se comporta como o adaptador real. Sem o contrato, os dois divergem em silêncio, e os testes que usam o fake passam a provar um comportamento que a produção não tem. E o que depende do banco (a restrição de unicidade, o rollback que desfaz duas tabelas, a trava da linha) não é provado por fake nenhum.

## Por que foi criado

Pedido de 2026-11-18: guidances que ensinem a implementar seguindo o projeto de referência `../scafold`, para usar em outros repositórios. A decisão que o sustenta é a ADR-010 (BDD com arquivos .feature como abordagem central dos testes de backend).

## Como implementar

Este guidance parte de [Testes com BDD e arquivos .feature](testes-com-bdd.md): a estrutura do `.feature`, os steps, `target_fixture`, o erro esperado em `outcome` e a fixture `run` são os mesmos.

### 1. Prepare o projeto

`testcontainers[postgres,rabbitmq]` entra no grupo `dev`; `markers` registra `contract` e `integration`, com o texto de `integration` dizendo que exige Docker; o override do mypy libera os módulos sem tipos. Veja [`pyproject.toml`](../scafold/pyproject.toml).

### 2. Suba o banco uma vez por sessão, migrado pelo Flyway

Em [`tests/conftest.py`](../scafold/tests/conftest.py):

- `_postgres_dsn` (sessão) cria uma rede, sobe o `PostgresContainer` com um alias nela, roda o Flyway num container na mesma rede (`_run_flyway`, com as pastas de `FLYWAY_LOCATIONS` montadas como volume somente leitura) e devolve a URL. O teste prova o caminho de produção: nome de arquivo, ordem de versão e histórico.
- `database_url` (cenário) esvazia as tabelas com `TRUNCATE`, menos `flyway_schema_history`.
- `persistence` monta a camada de dados como o processo a monta (`open_persistence`), sobre o loop do cenário, e a fecha no fim.
- **Pedir `database_url` é o que exige Docker.** Um teste que não pede essa fixture, nem outra que dependa dela, roda sem Docker.

O broker segue a mesma ideia: `rabbitmq_url` (sessão), em [`test_rabbitmq_dispatcher.py`](../scafold/tests/infrastructure/test_rabbitmq_dispatcher.py), sobe o `RabbitMqContainer`, e o `Dado` declara a exchange e a fila que o cenário precisa.

### 3. Escreva o contrato contra a porta

Um `.feature` com a tag `@contract`, cujos cenários descrevem o comportamento da porta sem dizer qual implementação está por trás: nenhum passo cita banco, tabela, fake ou memória. Veja [`example_repository_contract.feature`](../scafold/tests/features/infrastructure/example_repository_contract.feature): o que se lê depois de gravar, o que não existe, o nome repetido, a escrita fora da transação e o erro que desfaz a gravação. Os steps, em [`test_example_repository_contract.py`](../scafold/tests/infrastructure/test_example_repository_contract.py), recebem a fixture `backend`, tipada pelas portas.

### 4. Rode o contrato contra o fake e contra o adaptador real

A fixture `backend` é parametrizada: `fake` devolve `FakeUnitOfWork`, `InMemoryExampleRepository` e `InMemoryExampleReader`; `postgres` leva a marca `integration` e pede `persistence` por `request.getfixturevalue`, então o banco só sobe quando esse parâmetro roda. No módulo de teste, `pytestmark = pytest.mark.usefixtures("backend")` é obrigatório: os testes gerados por `scenarios` só pedem fixtures quando um step as pede, e a fixture parametrizada precisa estar declarada para gerar um teste por parâmetro. Cada cenário vira dois testes, `[fake]` e `[postgres]`. Ao mudar a porta, mude o `.feature` primeiro.

### 5. Escreva os cenários que só o real prova

Um `.feature` com a tag `@integration`, com os steps construindo o adaptador real direto, sem a fixture `backend`, e sem repetir o que o contrato já prova:

- [`outbox_persistence.feature`](../scafold/tests/features/infrastructure/outbox_persistence.feature): o evento gravado na transação que commita fica pendente e carimbado com o id do trace; o rollback não deixa nem o estado nem a mensagem; a drenagem reivindica e publica. A gravação roda dentro de um span aberto pelo step, como a borda faria.
- [`rabbitmq_dispatcher.feature`](../scafold/tests/features/infrastructure/rabbitmq_dispatcher.feature): a publicação aceita e o destino inexistente como falha permanente.

### 6. Rode com e sem Docker

| Comando | O que roda | Exige Docker |
|---|---|---|
| `uv run pytest -m "not integration"` | tudo, com o contrato só contra o fake | não |
| `uv run pytest -m contract` | o contrato contra o fake e contra o Postgres | sim |
| `uv run pytest -m integration` | tudo o que usa Postgres ou RabbitMQ | sim |
| `uv run pytest` | todos os cenários | sim |

O relatório de cobertura de uma execução sem Docker mostra os adaptadores reais sem cobertura. Isso é esperado.

## Guidances relacionados

- [Testes com BDD e arquivos .feature](testes-com-bdd.md) (v1.0.0): a base deste guidance.
- [Repositório e leitor sobre o querier do sqlc](repositorio-e-leitor-sobre-sqlc.md) (v1.0.0): o adaptador que o contrato exercita.
- [Migrations e queries SQL](migrations-e-queries-sql.md) (v1.0.0): as migrations que o Flyway aplica nos testes.
- [Evento de integração pela outbox](evento-de-integracao-pela-outbox.md) (v1.0.0): o que os cenários de integração da outbox provam.

## Change log

| Versão | Data       | Pessoa           | Motivo                                                                                   |
|--------|------------|------------------|------------------------------------------------------------------------------------------|
| 1.0.0  | 2026-11-18 | Guilherme Giusti | Criação: ensinar testes de contrato e de integração com Postgres e RabbitMQ reais, com o scaffold como referência |

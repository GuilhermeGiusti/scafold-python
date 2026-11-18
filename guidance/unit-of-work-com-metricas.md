---
title: Unit of Work com métricas
version: 1.0.0
---

# Unit of Work com métricas

## Propósito

Depois de ler, você saberá abrir uma transação num use case de escrita com `unit_of_work.transaction("<nome>")`, e verá como a `UnitOfWork` guarda a transação numa `ContextVar`, trata o aninhamento, entrega a conexão a repositórios e leitores (`write_querier` para escrever, `querier` para ler) e mede cada transação e cada query, com um span cada. A referência é [`infrastructure/persistence/`](../scafold/src/scafold/infrastructure/persistence/).

## Problema que resolve

Sem um padrão, cada módulo abriria transação de um jeito, e as transações ficariam sem medição. As armadilhas abaixo estão descritas nas docstrings da referência:

- A transação num atributo da `UnitOfWork`, que é uma só no processo, faria duas requisições concorrentes dividirem a mesma transação.
- Uma escrita feita pela conexão do pool, fora da transação, é revertida pelo SQLAlchemy na devolução, e se perde sem erro.
- Um `SAVEPOINT` no aninhamento deixaria o trecho interno sobreviver a um erro que deve reverter tudo.
- Os limites padrão dos histogramas do SDK foram pensados para milissegundos; em segundos, toda transação cairia no primeiro bucket.

## Por que foi criado

Pedido de 2026-11-18: guidances que ensinem a implementar seguindo o projeto de referência `../scafold`, para usar em outros repositórios. As decisões que o sustentam são a ADR-004 (Unit of Work com transação nomeada, repositórios e leitores) e a ADR-005 (Métrica obrigatória de transações e queries).

## Como implementar

### 1. Abrir a transação no use case de escrita

Só o use case de escrita abre a transação; o de leitura não abre. O use case recebe a porta `IUnitOfWork`, em [`domain/shared/persistence/unit_of_work.py`](../scafold/src/scafold/domain/shared/persistence/unit_of_work.py), e abre a transação só em volta da gravação. Sair do bloco sem erro commita; erro dentro dele reverte e sobe. Veja `CreateExampleUseCase.execute` e a constante `TRANSACTION_NAME`, em [`create_example_use_case.py`](../scafold/src/scafold/applications/usecases/create_example_use_case.py).

Regras do nome da transação:

- literal fixo em snake_case, o nome do use case sem o sufixo;
- nunca leva id, rótulo ou dado da requisição, que criaria uma série de métrica por valor;
- fica numa constante do módulo do use case.

Monte e valide o agregado antes do bloco, e faça I/O externo fora dele: cada instante dentro da transação prende uma conexão do pool. Os eventos de domínio são recolhidos dentro do bloco e despachados depois dele.

### 2. Pedir a conexão: `write_querier` e `querier`

Os dois ficam na `UnitOfWork` concreta, em [`unit_of_work.py`](../scafold/src/scafold/infrastructure/persistence/unit_of_work.py), e não na porta, porque devolvem conexão do driver. Recebem o nome fixo de quem pede (`"example_repository"`), que rotula as queries. `querier` entrega a conexão da transação ativa ou, sem transação, uma conexão do pool só para ler. `write_querier` recusa fora da transação com `OutsideUnitOfWork`.

### 3. A transação vive numa `ContextVar`

A conexão, o nome da transação e o repositório que pediu ficam nas `ContextVar` `_connection`, `_transaction_name` e `_repository`, no topo de `unit_of_work.py`.

### 4. Abrir, aninhar, commitar e medir

`transaction(name)` participa da transação já aberta no fluxo (o aninhado não commita, não reverte e não mede) ou abre a conexão, faz `BEGIN` e mede até o COMMIT ou o ROLLBACK. O status sai da marca `body_finished`, posta depois do `yield`: `rolled_back` quando o bloco levantou, `commit_failed` quando a falha veio do COMMIT. O `except` captura `BaseException`, porque cancelamento também reverte. Veja `UnitOfWork._open`.

### 5. As métricas

| Métrica (no Prometheus) | Instrumento OpenTelemetry | Rótulos |
|---|---|---|
| `db_transactions_total` | `db.transactions` | `transaction`, `status`, `error_type` |
| `db_transaction_duration_seconds` | `db.transaction.duration` (`s`) | `transaction`, `status` |
| `db_transactions_in_flight` | `db.transactions.in_flight` | `transaction` |
| `db_query_duration_seconds` | `db.query.duration` (`s`) | `repository`, `query`, `transaction`, `status` |

A porta é `IPersistenceMetrics`, em [`metrics/persistence_metrics.py`](../scafold/src/scafold/infrastructure/persistence/metrics/persistence_metrics.py), com os tipos `TransactionStatus` e `QueryStatus`. Os adaptadores são `OpenTelemetryPersistenceMetrics`, com `DURATION_BUCKETS_SECONDS` passados em `explicit_bucket_boundaries_advisory`, e `LoggingPersistenceMetrics`, que escreve em DEBUG.

### 6. Medir as queries sem tocar no código gerado

Toda query gerada pelo sqlc começa com `-- name: <query>`. Um ouvinte de eventos do SQLAlchemy lê esse nome e mede cada execução, com `repository` e `transaction` tirados das `ContextVar`. Veja `query_name` e `instrument_queries`, em [`query_metrics.py`](../scafold/src/scafold/infrastructure/persistence/query_metrics.py). SQL que não veio do sqlc não é medido.

### 7. Os spans

A transação externa abre `db.transaction <nome>`, corrente enquanto o bloco roda, e cada query abre `db.query <query>`, filho dele. Nomes e atributos estão em [`persistence_spans.py`](../scafold/src/scafold/infrastructure/persistence/persistence_spans.py); da falha sai só o nome da classe, por `mark_failed`. Sem `TracerProvider`, nenhum span é criado e a medição segue.

### 8. Montar uma vez por processo

Engine, ouvinte e Unit of Work são montados juntos por `open_persistence`, em [`persistence.py`](../scafold/src/scafold/infrastructure/persistence/persistence.py), com a mesma porta de métricas e o `TracerProvider` do processo. `DATABASE_URL` é `postgresql://`, sem driver; quem acrescenta o `+asyncpg` e traduz `sslmode` é `connect_arguments`, em [`engine.py`](../scafold/src/scafold/infrastructure/persistence/engine.py). Criar o engine não conecta. `Persistence.close()` devolve o pool no encerramento, no mesmo event loop.

### 9. Testar

A `FakeUnitOfWork`, em [`tests/support/fakes.py`](../scafold/tests/support/fakes.py), tira uma cópia do store na transação externa e a devolve se o bloco levantar, e guarda os nomes em `opened` e `committed`. O fake e a Unit of Work SQL passam pelo mesmo contrato em [`example_repository_contract.feature`](../scafold/tests/features/infrastructure/example_repository_contract.feature) (o cenário "o erro dentro da transação desfaz a gravação"). Os adaptadores de métricas são provados em [`metrics_adapters.feature`](../scafold/tests/features/infrastructure/metrics_adapters.feature).

## Quando não se aplica

Leitura não precisa de transação: o repositório ou o leitor pede `querier(...)` e a query sai com `transaction="none"`. Abra transação para ler só quando a leitura precisar de estado consistente com uma escrita do mesmo bloco, como `ArchiveExampleUseCase`.

## Guidances relacionados

- [Repositório e leitor sobre o querier do sqlc](repositorio-e-leitor-sobre-sqlc.md) (v1.0.0): como o repositório grava pelo `write_querier` e o leitor lê pelo `querier`.
- [Geração de código com sqlc](geracao-de-codigo-com-sqlc.md) (v1.0.0): de onde vem o comentário `-- name:`.
- [Telemetria com OpenTelemetry](telemetria-com-opentelemetry.md) (v1.0.0): como montar o `TracerProvider` e escolher os adaptadores.

## Change log

| Versão | Data       | Pessoa           | Motivo                                                                                   |
|--------|------------|------------------|------------------------------------------------------------------------------------------|
| 1.0.0  | 2026-11-18 | Guilherme Giusti | Criação: ensinar a abrir transação medida pela Unit of Work com o scaffold como referência |

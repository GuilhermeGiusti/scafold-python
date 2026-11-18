---
title: Commands, queries e use cases
version: 1.0.0
---

# Commands, queries e use cases

## Propósito

Depois de ler, você saberá escrever um command ou uma query, escrever o use case que o executa seguindo um dos oito contratos, dar a ele os erros de aplicação certos e entregá-lo às bordas envolvido pelo decorator de observabilidade. A referência é [`applications/`](../scafold/src/scafold/applications/) e `build_use_cases`, em [`bootstrap/composition.py`](../scafold/src/scafold/bootstrap/composition.py).

## Problema que resolve

Sem uma forma comum, cada use case define o `execute` do seu jeito (argumentos soltos, métodos com nomes próprios), e toda borda que o chama (HTTP, linha de comando, tela, agendador) fica acoplada a essas diferenças. Com um único objeto de entrada e um contrato herdado explicitamente, o mypy recusa a assinatura errada na definição da classe, e um decorator tipado envolve qualquer use case.

## Por que foi criado

Pedido de 2026-11-18: guidances que ensinem a implementar seguindo o projeto de referência `../scafold`, para usar em outros repositórios. A decisão que o sustenta é a ADR-008 (Commands, queries e use cases na camada de aplicação).

## Como implementar

### 1. Escolha o contrato pelo que `execute` recebe e devolve

Os oito contratos estão em [`applications/shared/use_case.py`](../scafold/src/scafold/applications/shared/use_case.py).

| Recebe   | Devolve  | Síncrono            | Assíncrono               | Na referência |
|----------|----------|---------------------|--------------------------|---------------|
| um input | um valor | `UseCase[I, O]`     | `AsyncUseCase[I, O]`     | `CreateExampleUseCase`, `GetExampleUseCase`, `ListExamplesUseCase` |
| um input | nada     | `UnitUseCase[I]`    | `AsyncUnitUseCase[I]`    | `ArchiveExampleUseCase` |
| nada     | um valor | `NullaryUseCase[O]` | `AsyncNullaryUseCase[O]` | `OutboxDrainUseCase` |
| nada     | nada     | `ExecuterUseCase`   | `AsyncExecuterUseCase`   | `PurgeArchivedExamplesUseCase` |

Use o assíncrono quando o use case espera I/O.

### 2. Escreva o command ou a query

O input é um único `@dataclass(frozen=True, slots=True, kw_only=True)` que só carrega dados: não valida regra, não acessa repositório e não sabe quem o executa. O id chega como `UUID`; quem o converte no tipo do domínio é o use case.

- Command em `applications/commands/`: `CreateExampleCommand`, em [`create_example_command.py`](../scafold/src/scafold/applications/commands/create_example_command.py), e `ArchiveExampleCommand`.
- Query em `applications/queries/`: `GetExampleQuery` e `ListExamplesQuery`, em [`list_examples_query.py`](../scafold/src/scafold/applications/queries/list_examples_query.py).

O use case sem input não tem command nem query. Quando ganhar filtro ou paginação, crie a query e troque o contrato: o mypy aponta todos os chamadores.

### 3. Escreva o use case

O use case fica em `applications/usecases/` e segue estas regras:

- **Herda o contrato explicitamente**, como `class CreateExampleUseCase(AsyncUseCase[CreateExampleCommand, ExampleId])`.
- **Recebe as dependências pelo construtor**, só por keyword, tipadas pelas portas (Unit of Work, repositório, gateway, gravador da outbox, dispatcher, relógio).
- **Nomeia o parâmetro de `execute` como `input`**, igual ao contrato.
- **Decide a ordem e deixa a regra com o domínio**: carrega, pede a transição ao agregado e grava.
- **O retorno é livre**, desde que siga o contrato. O command de criação devolve o id criado.

Modelos: [`create_example_use_case.py`](../scafold/src/scafold/applications/usecases/create_example_use_case.py) (consulta externa e validação fora da transação; gravação, outbox e recolha de eventos dentro dela; despacho depois do commit) e [`archive_example_use_case.py`](../scafold/src/scafold/applications/usecases/archive_example_use_case.py) (carregar, transicionar e gravar na mesma transação). A transação está em [Unit of Work com métricas](unit-of-work-com-metricas.md); o despacho de eventos, em [Handler de evento de domínio](handler-de-evento-de-dominio.md).

### 4. Devolva DTO, não o agregado

A query devolve um DTO imutável, e o agregado não sai do use case. O DTO fica em `applications/queries/`, ao lado da query, e o mapeamento do agregado para ele fica no próprio DTO: `ExampleView.from_aggregate`, em [`example_view.py`](../scafold/src/scafold/applications/queries/example_view.py). Quando a leitura vem de um leitor dedicado, o DTO também mora em `queries/`: `ExampleSummary`.

### 5. Erros de aplicação herdam de `ApplicationError`

Falha sai como exceção, nunca como `False` ou `None`. Erro de aplicação é resposta ao pedido ("o que foi pedido não existe") e herda de `ApplicationError`, em [`application_error.py`](../scafold/src/scafold/applications/errors/application_error.py): veja `ExampleNotFound`. Regra violada é erro de domínio e não herda dessa base. Cada borda traduz os dois pelo seu presenter.

### 6. Entregue o use case envolvido pelo decorator

Nenhum use case chega cru à borda. Em `build_use_cases`, cada um é montado e envolvido pelo decorator do seu contrato:

| Contrato | Decorator |
|---|---|
| os quatro síncronos | `ObservedUseCase` e os demais, em [`observed_use_cases.py`](../scafold/src/scafold/infrastructure/observability/observed_use_cases.py) |
| as versões `Async*` | `AsyncObservedUseCase` e os demais, em [`async_observed_use_cases.py`](../scafold/src/scafold/infrastructure/observability/async_observed_use_cases.py) |

Ao montar um use case novo:

- Passe o rótulo `use_case` como literal em snake_case, o nome do use case sem o sufixo (`CreateExampleUseCase` vira `"create_example"`). Renomear quebra a série de métrica.
- Declare o campo em `UseCases` com o tipo do contrato, e não com a classe concreta.
- `build_use_cases` recebe só portas: o mesmo código monta os use cases sobre o banco (`build_foundation`) e sobre os fakes (`build_scene`, em [`tests/support/scene.py`](../scafold/tests/support/scene.py)).

O decorator delega a `UseCaseObserver.observe`, em [`use_case_observer.py`](../scafold/src/scafold/infrastructure/observability/use_case_observer.py): abre o span `use_case <nome>`, registra início e fim em DEBUG, emite `use_case_executions_total` e `use_case_duration_seconds` pela porta `IUseCaseMetrics`, registra a falha em ERROR e relança. Do erro, o span leva só o nome da classe.

### 7. O que não fazer

- Não decida comportamento com `isinstance` contra os contratos: em runtime eles só conferem se existe um `execute`.
- Não receba argumentos soltos em `execute`.
- Não escreva código genérico que aceite use case síncrono e assíncrono pelo mesmo contrato: quem chama receberia uma corrotina que ninguém aguarda.

### 8. Testar

Os cenários de aplicação usam os use cases montados sobre os fakes: [`create_example.feature`](../scafold/tests/features/applications/create_example.feature), [`archive_example.feature`](../scafold/tests/features/applications/archive_example.feature) e [`read_examples.feature`](../scafold/tests/features/applications/read_examples.feature). O decorator é provado em [`use_case_observation.feature`](../scafold/tests/features/infrastructure/use_case_observation.feature).

## Guidances relacionados

- [Unit of Work com métricas](unit-of-work-com-metricas.md) (v1.0.0): como o command abre a transação e a nomeia.
- [Repositório e leitor sobre o querier do sqlc](repositorio-e-leitor-sobre-sqlc.md) (v1.0.0): como o leitor devolve o DTO sem reconstruir o agregado.
- [Handler de evento de domínio](handler-de-evento-de-dominio.md) (v1.0.0): quem trata os eventos despachados.
- [Evento de integração pela outbox](evento-de-integracao-pela-outbox.md) (v1.0.0): o gravador chamado dentro da transação e a drenagem, um use case sem input.
- [Montagem do processo e pontos de entrada](montagem-e-pontos-de-entrada.md) (v1.0.0): onde `build_use_cases` é chamado.

## Change log

| Versão | Data       | Pessoa           | Motivo                                                                                   |
|--------|------------|------------------|------------------------------------------------------------------------------------------|
| 1.0.0  | 2026-11-18 | Guilherme Giusti | Criação: ensinar a escrever commands, queries e use cases com o scaffold como referência |

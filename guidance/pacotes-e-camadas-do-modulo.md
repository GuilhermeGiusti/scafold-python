---
title: Pacotes e camadas de um módulo
version: 1.0.0
---

# Pacotes e camadas de um módulo

## Propósito

Depois de ler, você saberá em qual pasta e em qual módulo fica cada peça de um módulo de backend: as do domínio, as da aplicação, os adaptadores da infraestrutura, a montagem e os pontos de entrada. Saberá também como nomear o módulo, como importar e onde ficam os testes. A referência é o projeto [`../scafold`](../scafold/README.md), com o pacote [`src/scafold/`](../scafold/src/scafold/).

## Problema que resolve

Sem uma resposta fixa para "onde coloco este arquivo?", cada agregado, evento, adaptador ou rota acaba num lugar diferente, os imports deixam de ser previsíveis e o lado de dentro (domínio e aplicação) passa a importar framework e banco sem ninguém perceber. Com a árvore fixa e um portão que lê os imports, a camada errada é acusada pelo teste.

## Por que foi criado

Pedido de 2026-11-18: um conjunto de guidances que ensine a implementar seguindo o projeto de referência `../scafold`, para usar em outros repositórios. A adoção de DDD vem da ADR-002 (Domain Driven Design nos módulos backend). As ADRs são citadas pelo número e pelo título; os arquivos delas não acompanham este conjunto.

## Como implementar

### 1. A árvore de um módulo

O pacote importável fica em `src/<pacote>/`, e o SQL, os pontos de entrada e os testes ficam fora dele, na raiz do módulo:

```text
src/<pacote>/
├── domain/
│   ├── shared/                      bases de todo contexto
│   │   ├── aggregates/aggregate_root.py
│   │   ├── entities/entity.py
│   │   ├── events/event_base.py     IDomainEvent, IDomainEventHandler, IDomainEventDispatcher
│   │   ├── events/domain_event.py   DomainEvent
│   │   └── persistence/unit_of_work.py   IUnitOfWork
│   ├── <contexto>/
│   │   ├── aggregates/  entities/  events/  errors/  value_objects/  repositories/
│   └── outbox/                      contexto técnico: value_objects/, ports/, errors/
├── applications/
│   ├── shared/use_case.py           os oito contratos
│   ├── commands/  queries/  errors/  ports/  usecases/  handlers/
├── infrastructure/
│   ├── persistence/                 Unit of Work, engine, métricas, spans
│   │   └── <contexto>/              repositório e leitor SQL, mappers/, sqlc/ gerado
│   ├── events/                      blinker e o gravador da outbox
│   ├── brokers/  scheduling/  external/  observability/
│   └── rest/  cli/  streamlit/      as bordas, cada uma com mappers/ e presenters/
└── bootstrap/                       configuração, telemetria, composição, montagem de cada processo
entrypoint/                          api.py, cli.py, streamlit_app.py, outbox_job.py
migrations/<contexto>/               schema, aplicado pelo Flyway
queries/<contexto>/                  o SQL que o sqlc transforma em código
tests/features/<camada>/             os .feature; tests/<camada>/test_*.py, os steps
```

Na referência, cada pasta corresponde a uma pasta de [`src/scafold/`](../scafold/src/scafold/). O bounded context de exemplo é [`domain/bounded_context_example/`](../scafold/src/scafold/domain/bounded_context_example/); o contexto técnico da outbox é [`domain/outbox/`](../scafold/src/scafold/domain/outbox/).

### 2. Um módulo por classe

Dentro de cada pasta, cada classe fica no próprio módulo, e o nome do módulo é o nome da classe em snake_case:

| Peça | Pasta | Na referência |
|---|---|---|
| Raiz do agregado | `domain/<contexto>/aggregates/` | `Example`, em [`example.py`](../scafold/src/scafold/domain/bounded_context_example/aggregates/example.py) |
| Entidade filha | `domain/<contexto>/entities/` | `ExampleItem`, em [`example_item.py`](../scafold/src/scafold/domain/bounded_context_example/entities/example_item.py) |
| Evento de domínio | `domain/<contexto>/events/` | `ExampleCreated`, em [`example_created.py`](../scafold/src/scafold/domain/bounded_context_example/events/example_created.py) |
| Erro de domínio | `domain/<contexto>/errors/` | `LabelTaken`, em [`label_taken.py`](../scafold/src/scafold/domain/bounded_context_example/errors/label_taken.py) |
| Identificador e valor | `domain/<contexto>/value_objects/` | `ExampleId`, `Category` |
| Porta do repositório | `domain/<contexto>/repositories/` | `IExampleRepository` |
| Command e query | `applications/commands/`, `applications/queries/` | `CreateExampleCommand`, `GetExampleQuery` |
| DTO de saída | `applications/queries/` | `ExampleView`, `ExampleSummary` |
| Erro de aplicação | `applications/errors/` | `ExampleNotFound` |
| Porta da aplicação | `applications/ports/` | `IExampleReader`, `ICategoryGateway` |
| Use case | `applications/usecases/` | `CreateExampleUseCase` |
| Handler de evento | `applications/handlers/` | `ExampleCreatedHandler` |
| Adaptador | `infrastructure/<assunto>/` | `SqlExampleRepository`, `RabbitmqDispatcher` |
| Mapper e presenter de borda | `infrastructure/<borda>/mappers/`, `.../presenters/` | `ExampleRequestMapper`, `ExamplePresenter` |

Todos os pacotes têm `__init__.py` vazio, e nada é reexportado por ele. Os erros pertencem ao contexto: um contexto não importa o erro de outro.

### 3. Imports absolutos, direto do módulo que define a classe

O bloco de imports de [`example.py`](../scafold/src/scafold/domain/bounded_context_example/aggregates/example.py) mostra o formato: import absoluto a partir do pacote, apontando o módulo da classe, como `scafold.domain.bounded_context_example.value_objects.example_id`. O nome do projeto e o do pacote ficam em [`pyproject.toml`](../scafold/pyproject.toml).

### 4. Quem importa quem

O domínio só importa a biblioteca padrão e o próprio domínio. A aplicação importa o domínio e a aplicação. A infraestrutura importa o lado de dentro e as bibliotecas. A montagem, em `bootstrap/`, é o único lugar que junta porta, adaptador e decorator. O ponto de entrada é o único que lê o ambiente. Essas fronteiras são cobradas pelo teste, como mostra [Portões de arquitetura](portoes-de-arquitetura.md).

### 5. Testes espelham as camadas

Os cenários ficam em [`tests/features/`](../scafold/tests/features/), uma pasta por camada (`domain`, `applications`, `infrastructure`, `rest`, `bootstrap`, `edges`, `architecture`), e os steps em `tests/<camada>/test_<assunto>.py`. Fakes, dublês e a montagem sobre eles ficam em [`tests/support/`](../scafold/tests/support/).

### 6. Idioma

Identificadores (classes, módulos, métodos, campos) em inglês. Docstrings, comentários e cenários em pt-BR.

### 7. Trocar o nome do pacote ao copiar a referência

Renomeie `src/scafold/`, substitua o nome em todos os imports, no [`pyproject.toml`](../scafold/pyproject.toml) (`name` e `source_pkgs`), no [`sqlc.yaml`](../scafold/sqlc.yaml) (`out` e `package`) e em `LOGGER_NAME` de [`composition.py`](../scafold/src/scafold/bootstrap/composition.py). Depois rode `make generate` e `make check`.

## Guidances relacionados

- [Montagem do processo e pontos de entrada](montagem-e-pontos-de-entrada.md) (v1.0.0): o que fica em `bootstrap/` e em `entrypoint/`.
- [Agregado raiz](agregado-raiz.md) (v1.0.0): a classe que fica em `aggregates/`.
- [Commands, queries e use cases](commands-queries-e-use-cases.md) (v1.0.0): as peças de `applications/`.
- [Portões de arquitetura](portoes-de-arquitetura.md) (v1.0.0): os testes que cobram as fronteiras.

## Change log

| Versão | Data       | Pessoa           | Motivo                                                                                   |
|--------|------------|------------------|------------------------------------------------------------------------------------------|
| 1.0.0  | 2026-11-18 | Guilherme Giusti | Criação: ensinar onde fica cada peça de um módulo, com o scaffold como referência, para uso em outros repositórios |

# scafold

Scaffold de um projeto Python em camadas, para copiar como ponto de partida de um repositório novo. Ele mostra, com um bounded context de exemplo que atravessa todas as camadas, como criar e manter domínio, aplicação, infraestrutura, montagem e pontos de entrada, seguindo os patterns das ADRs e dos guidances. As bibliotecas, as versões e a lista completa de patterns estão em [`stack.md`](stack.md).

Os quatro pontos de entrada chamam os mesmos use cases, montados pelo mesmo código:

| Ponto de entrada | O que sobe | Comando |
|---|---|---|
| [`entrypoint/api.py`](entrypoint/api.py) | API REST com FastAPI; Swagger em `/docs`; health check em `GET /api/v1/health/check` | `make api` |
| [`entrypoint/cli.py`](entrypoint/cli.py) | um comando no shell, com resultado em JSON | `make cli ARGS="list-examples"` |
| [`entrypoint/streamlit_app.py`](entrypoint/streamlit_app.py) | tela Streamlit que cria, lista e arquiva | `make streamlit` |
| [`entrypoint/outbox_job.py`](entrypoint/outbox_job.py) | job que drena a outbox para o RabbitMQ, por cron | `make outbox-job` |

## Começar

```bash
uv sync                      # Python 3.14 e as dependências do uv.lock
cp .env.example .env         # ajuste se precisar
make stack-up migrate-up     # Postgres, RabbitMQ, Prometheus, Jaeger e as migrations
make api                     # http://127.0.0.1:8000/docs
make test-unit               # os cenários que rodam sem Docker
make check                   # mypy, sqlc-check, sqlc-vet e todos os testes (exige Docker)
```

O health check não consulta o banco, então `make api` responde em `/api/v1/health/check` mesmo com a stack desligada. As rotas de Example precisam do Postgres migrado.

**O log.** Por padrão, só WARNING e ERROR aparecem. Com `LOG_DEBUG=true`, tudo aparece, a partir de DEBUG: início e fim de cada use case, as medições escritas no log e a saída dos handlers. Toda linha é um JSON com `timestamp`, `level`, `logger`, `message`, `service`, `trace_id` e `span_id`; uma exceção sai com a classe e a pilha, nunca com a mensagem.

**Para usar em outro repositório**, troque o nome do pacote: renomeie `src/scafold/`, substitua `scafold` em todos os imports, no `pyproject.toml` (`name` e `source_pkgs`), no `sqlc.yaml` (`out` e `package`) e em `LOGGER_NAME` de `bootstrap/composition.py`, e rode `make generate` e `make check`.

## As camadas

```text
src/scafold/
├── domain/                     regras de negócio; só a biblioteca padrão
│   ├── shared/                 AggregateRoot, Entity, contratos de evento, porta IUnitOfWork
│   ├── bounded_context_example/
│   │   ├── aggregates/         a raiz (Example)
│   │   ├── entities/           as filhas (ExampleItem)
│   │   ├── events/             os fatos (ExampleCreated...)
│   │   ├── errors/             as regras violadas (InvalidLabel...)
│   │   ├── value_objects/      ids (NewType) e valores (Category)
│   │   └── repositories/       a porta do repositório (IExampleRepository)
│   ├── bounded_context_order/  estado modelado por tipos (um tipo por estado)
│   └── outbox/                 contexto técnico da outbox: valores, portas e erros
├── applications/               a ordem das coisas; não conhece framework nem banco
│   ├── shared/use_case.py      os 8 contratos de use case
│   ├── commands/ queries/      o input de cada use case, e os DTOs de saída
│   ├── errors/                 ApplicationError e os erros de aplicação
│   ├── ports/                  portas da aplicação (leitor, gateway externo, métricas da outbox)
│   ├── usecases/               os use cases
│   └── handlers/               os handlers de evento de domínio
├── infrastructure/             os adaptadores: tudo o que fala com o mundo
│   ├── persistence/            Unit of Work, engine, métricas e spans, repositórios SQL, sqlc/
│   ├── events/                 blinker (dispatcher e manager) e o gravador da outbox
│   ├── brokers/ scheduling/    a Strategy RabbitMQ e o agendador cron
│   ├── external/               o serviço externo, com o mapper anti-corrupção
│   ├── observability/          decorators de use case, métricas, log JSON, span de envio
│   └── rest/ cli/ streamlit/   as bordas, cada uma com mappers/ e presenters/
└── bootstrap/                  a montagem: configuração, telemetria, composição, cada processo
entrypoint/                     main de cada processo; o único lugar que lê os.environ
migrations/<contexto>/          schema, aplicado pelo Flyway
queries/<contexto>/             o SQL que o sqlc transforma em código
tests/features/<camada>/        os cenários .feature; tests/<camada>/test_*.py, os steps
```

**A regra de dependência.** `domain` só importa `domain`. `applications` importa `domain` e `applications`. `infrastructure` importa tudo de dentro e as bibliotecas. `bootstrap` é o único que junta porta, adaptador e decorator. O portão [`tests/architecture/test_boundaries.py`](tests/architecture/test_boundaries.py) reprova o import errado, e outro reprova quem ler o ambiente fora de `entrypoint/`.

**O caminho de uma escrita**, de `POST /api/v1/examples`:

1. O FastAPI valida o corpo contra `CreateExampleRequest` (tipos estritos, campo desconhecido recusado) e abre o span da requisição.
2. `ExampleRequestMapper` traduz o schema HTTP em `CreateExampleCommand` (`displayName` vira `label`).
3. O controller chama `use_cases.create_example`, que é o decorator `AsyncObservedUseCase`: abre o span `use_case create_example`, mede e registra.
4. `CreateExampleUseCase` consulta o serviço externo pela porta `ICategoryGateway` (o mapper anti-corrupção traduz o `tier` em `Category`), e `Example.create` valida e registra `ExampleCreated`. Tudo fora da transação.
5. Dentro de `unit_of_work.transaction("create_example")`: o repositório grava pelo `write_querier` e pelo código do sqlc, com o `ExampleRowMapper`; o gravador da outbox grava o evento de integração na mesma transação; os eventos de domínio são recolhidos.
6. Depois do commit, os eventos de domínio vão aos handlers pelo `blinker`.
7. `ExamplePresenter` monta a resposta. Um erro sobe sem `try`/`except` e o exception handler o entrega à tabela do presenter, a mesma que documenta a rota no Swagger.
8. Mais tarde, o job da outbox reivindica a linha, publica no RabbitMQ pela Strategy e marca o resultado, continuando o trace de quem gravou.

## Como criar cada peça

Cada receita aponta o arquivo do scaffold que serve de modelo. O nome do guidance de cada assunto está em [`stack.md`](stack.md), seção 5.

### Um bounded context novo

1. Crie `domain/<contexto>/` com as subpastas `aggregates/`, `entities/`, `events/`, `errors/`, `value_objects/` e `repositories/`, cada uma com `__init__.py` vazio. Nada é reexportado pelo `__init__.py`.
2. Um módulo por classe, com o nome da classe em snake_case. Imports absolutos, direto do módulo que define a classe.
3. Os erros pertencem ao contexto: um contexto não importa o `InvalidTransition` do outro.
4. Crie `migrations/<contexto>/` e `queries/<contexto>/`, um bloco novo no `sqlc.yaml` (copie o do `example`, trocando `schema`, `queries`, `out` e `package`) e uma location nova no `FLYWAY_LOCATIONS` do `docker-compose.yml` e do `tests/conftest.py`.

### Agregado, entidade, value object, evento e erro

- **Identificador**: `NewType` sobre `UUID` em `value_objects/` ([`example_id.py`](src/scafold/domain/bounded_context_example/value_objects/example_id.py)).
- **Raiz**: `@dataclass(eq=False)` que estende `AggregateRoot[IdT]` e implementa `get_id`. Fábrica `create` que valida, cria e registra o evento. Toda operação valida, muda o estado e só então chama `add_event`. Instante e dados externos chegam por parâmetro ([`example.py`](src/scafold/domain/bounded_context_example/aggregates/example.py)).
- **Entidade filha**: `@dataclass(eq=False)` que estende `Entity[IdT]`; só a raiz a cria, num método que valida, cria, adiciona e registra o evento ([`example_item.py`](src/scafold/domain/bounded_context_example/entities/example_item.py), `Example.add_item`).
- **Evento**: `@dataclass(eq=False)` que estende `DomainEvent`, com nome no passado, `versioning()` começando em `"1"`, `name()` no formato `<contexto>.<agregado>.<fato>` e `to_json()` com todos os campos ([`example_created.py`](src/scafold/domain/bounded_context_example/events/example_created.py)). O `name()` vira rótulo de métrica: renomear quebra a série.
- **Erro de domínio**: subclasse de `Exception` no próprio módulo, com a regra violada na docstring e na mensagem, sem repetir o dado recebido.

### Estado modelado por tipos

Quando o objeto tem estados com campos e transições diferentes, faça um `@dataclass(frozen=True, slots=True)` por estado, com a transição como método do estado de origem que devolve o de destino, a união `type Order = ...` e `match` terminando em `assert_never` ([`order.py`](src/scafold/domain/bounded_context_order/aggregates/order.py)). A garantia só vale com o mypy rodando.

### Command, query e use case

1. O input é um `@dataclass(frozen=True, slots=True, kw_only=True)` em `applications/commands/` (muda estado) ou `applications/queries/` (só lê). O id chega como `UUID`.
2. Escolha o contrato pelo que `execute` recebe e devolve (`AsyncUseCase`, `AsyncUnitUseCase`, `AsyncNullaryUseCase`, `AsyncExecuterUseCase`, e as versões síncronas) e herde dele explicitamente. O parâmetro se chama `input`.
3. Dependências pelo construtor, só por keyword, tipadas pelas portas. A regra fica no agregado; o use case decide a ordem.
4. O use case de escrita abre `unit_of_work.transaction(TRANSACTION_NAME)` só em volta da gravação. O nome é um literal em snake_case, o nome do use case sem o sufixo, numa constante do módulo. Monte e valide o agregado antes do bloco.
5. Eventos de domínio: `collect` dentro do bloco, `dispatch` depois dele.
6. A query devolve DTO, nunca o agregado. Falha sai como exceção; "não existe" é erro de aplicação (herda de `ApplicationError`).
7. Registre o use case em `build_use_cases` ([`composition.py`](src/scafold/bootstrap/composition.py)), envolvido pelo decorator do contrato, com o rótulo literal, e declare o campo em `UseCases` com o tipo do contrato. Nenhum use case chega cru à borda.

Modelos: [`create_example_use_case.py`](src/scafold/applications/usecases/create_example_use_case.py) (escrita com outbox e eventos), [`archive_example_use_case.py`](src/scafold/applications/usecases/archive_example_use_case.py) (carregar, transicionar, gravar), [`list_examples_use_case.py`](src/scafold/applications/usecases/list_examples_use_case.py) (leitura pelo leitor).

### Persistência de um agregado

1. **Migration** em `migrations/<contexto>/V<AAAAMMDDHHMMSS>__<descricao>.sql`, com o instante de criação em UTC. O schema só recusa: nenhuma trigger, function, rule nem `DEFAULT` de instante. Toda restrição tem nome `pk_`, `fk_`, `uq_` ou `ck_` + `<tabela>_<coluna(s)>`. Migration aplicada não se edita: a mudança é um arquivo novo.
2. **Queries** em `queries/<contexto>/<agregado>_write.sql` e `_read.sql`, cada uma com `-- name: <NomeEmPascalCase> :exec|:one|:many|:execrows` e parâmetros `sqlc.arg(nome)`. Não use `:copyfrom` nem `:batch*`.
3. `make generate` e commite o SQL e a pasta `sqlc/` juntos. O código gerado nunca é editado à mão; `make sqlc-check` acusa quando ele fica para trás.
4. **Porta** em `domain/<contexto>/repositories/`, só com agregado, id e erro de domínio.
5. **Mapper de persistência** em `infrastructure/persistence/<contexto>/mappers/`, com `to_row` e `to_aggregate`; reconstrói pelo construtor, e não pela fábrica ([`example_row_mapper.py`](src/scafold/infrastructure/persistence/bounded_context_example/mappers/example_row_mapper.py)).
6. **Repositório SQL** ao lado da pasta `sqlc/`, com a constante `REPOSITORY_NAME`. Escreve pelo `write_querier` (que recusa fora da transação), lê pelo `querier`, consome o `:many` dentro do bloco e traduz a violação de restrição pelo nome ([`sql_example_repository.py`](src/scafold/infrastructure/persistence/bounded_context_example/sql_example_repository.py)).
7. **Fake** em [`tests/support/fakes.py`](tests/support/fakes.py), sobre o mesmo store da `FakeUnitOfWork`, recusando escrita fora da transação.
8. **Contrato**: um `.feature` `@contract` que roda contra o fake e contra o Postgres pela fixture `backend` ([`example_repository_contract.feature`](tests/features/infrastructure/example_repository_contract.feature)).

Para a leitura que só mostra dados, crie o **leitor dedicado**: porta em `applications/ports/`, DTO em `applications/queries/`, adaptador ao lado do repositório com `READER_NAME`, e a query faz o trabalho que o agregado faria em memória ([`sql_example_reader.py`](src/scafold/infrastructure/persistence/bounded_context_example/sql_example_reader.py)).

### Handler de evento de domínio

Classe em `applications/handlers/<evento>_handler.py` com `listener_to()` e `handle(event)`. A saída chega pelo construtor como função; não há `try`/`except`, porque o `DomainEventManager` mede, registra a falha e segue para o próximo handler. Registre em `build_event_manager` ([`composition.py`](src/scafold/bootstrap/composition.py)) com a saída dele. Modelo: [`example_created_handler.py`](src/scafold/applications/handlers/example_created_handler.py).

### Evento de integração pela outbox

1. No use case de escrita, monte um `IntegrationEvent` com o destino **lógico** e chame `writer.write(event)` **dentro** da transação que grava o estado (`example_created_event` em [`create_example_use_case.py`](src/scafold/applications/usecases/create_example_use_case.py)). Nunca publique no broker de dentro do código que muda o estado.
2. O gravador exige um span corrente (o decorator do use case abre um) e o carimbo de `OUTBOX_DISPATCHER`.
3. O job drena uma mensagem por transação e decide: publicada, reagendada até 5 tentativas, ou morta.

**Uma Strategy nova** (outro broker): uma classe que cumpre `IDispatcher` em `infrastructure/brokers/`, que publica e relata sem lançar, sem contar tentativas, sem gravar e sem abrir span; o carimbo em `KNOWN_DISPATCHERS` ([`dispatchers.py`](src/scafold/domain/outbox/dispatchers.py)); uma migration nova com o carimbo no `CHECK` e a tabela de dados de envio; e a montagem em [`outbox_job.py`](src/scafold/bootstrap/outbox_job.py), envolvida pelo `TracedDispatcher`.

### Rota REST

1. **Schema de entrada** que herda de `RequestSchema`: todo campo com tipo, restrição, exemplo e docstring; `StrictStr`/`StrictInt` para texto e número; o nome do contrato em `alias` ([`example_schemas.py`](src/scafold/infrastructure/rest/example_schemas.py)).
2. **Schema de saída** que herda de `ResponseSchema`, com o nome do contrato em `serialization_alias`. Lista tem schema próprio.
3. **Mapper de entrada** e **presenter** do agregado. O presenter herda de `ErrorPresenter` e declara `_ERRORS` (status, código, texto e quando acontece) e `PRESENTABLE`.
4. **Controller**: `add_api_route` com `summary`, `description`, `status_code`, `response_model`, `response_description` e `responses=presenter.documented_errors(...)`. Rota sem entrada passa `validation=False`.
5. Registre o controller e o presenter em [`bootstrap/api.py`](src/scafold/bootstrap/api.py). As rotas ganham o prefixo `/api/v1`.
6. Escreva os cenários por status em `tests/features/rest/`. As 8 regras do OpenAPI e o Schemathesis já percorrem toda rota nova sem mudar teste.

### Comando de CLI e página Streamlit

- **CLI**: declare o comando em `ExampleCli.add_commands` (o `argparse` confere tipo e restrição), traduza no mapper de argumentos e apresente no presenter da CLI ([`example_cli.py`](src/scafold/infrastructure/cli/example_cli.py)). Outro agregado ganha a sua classe e entra em `build_parser` ([`bootstrap/cli.py`](src/scafold/bootstrap/cli.py)).
- **Streamlit**: uma página em `infrastructure/streamlit/` que recebe os use cases e o `run`, com mapper do formulário e presenter da tela ([`example_page.py`](src/scafold/infrastructure/streamlit/example_page.py)), montada em [`bootstrap/streamlit_app.py`](src/scafold/bootstrap/streamlit_app.py).

### Serviço externo

Porta em `applications/ports/` no vocabulário do domínio; adaptador em `infrastructure/external/` com o mapper anti-corrupção em `mappers/`; termo desconhecido vira erro próprio de infraestrutura, registrado no log e contado em `external_translation_errors_total{gateway}` antes de relançar ([`external_category_gateway.py`](src/scafold/infrastructure/external/external_category_gateway.py)). O [`fake_category_api.py`](src/scafold/infrastructure/external/fake_category_api.py) faz o papel do cliente HTTP do fornecedor: troque-o pelo cliente real.

### Métrica, span e variável de ambiente

- **Porta de métricas nova**: o `Protocol` ao lado de quem a consome, dois adaptadores (OpenTelemetry e log em DEBUG), e uma entrada em `MetricsAdapters`/`build_metrics_adapters`. Rótulos só com nomes fixos: nunca id, caminho, mensagem nem dado do pedido.
- **Span novo**: o `TracerProvider` entra pelo construtor (vazio é no-op, nunca o global); nome é prefixo fixo mais nome do catálogo; os atributos são os rótulos da métrica correspondente; `record_exception=False` e `set_status_on_exception=False`, marcando a falha só com a classe da exceção.
- **Variável de ambiente nova**: só em `bootstrap/settings.py` (ou `job_settings.py`), pelas funções `required`, `switch`, `positive_integer`. Interruptor aceita só `true` e `false`; a recusa cita a variável e nunca o valor. Documente em `.env.example`.

### Teste

Primeiro o cenário, em `tests/features/<camada>/<assunto>.feature`, com `# language: pt`, `Regra:`, dados concretos e a recusa dita na língua do negócio (`Então a operação é recusada por nome já usado`). Depois um `tests/<camada>/test_<assunto>.py` com `scenarios(...)` e os steps, todos chamados `_`. O estado passa por `target_fixture`; o `Quando` devolve o erro esperado em `outcome`; um motivo novo de recusa entra em `REASONS` ([`tests/conftest.py`](tests/conftest.py)). Código async roda pela fixture `run`. Toda tag nova é registrada em `markers` no `pyproject.toml`.

| Comando | O que roda |
|---|---|
| `uv run pytest -m "not integration"` | tudo o que roda sem Docker |
| `uv run pytest -m contract` | o contrato contra o fake e contra o Postgres (Docker) |
| `uv run pytest -m integration` | tudo o que usa Postgres ou RabbitMQ (Docker) |
| `uv run pytest -m fuzz` | só as requisições geradas pelo Schemathesis |
| `uv run mypy` | `strict` em `src`, `tests` e `entrypoint` |

## Como manter

- **`make check` antes de cada commit**: tipos, código gerado em dia, queries válidas contra o banco e toda a suíte.
- **Mudou o SQL?** `make generate` e commite o SQL e o `sqlc/` juntos. Migration já aplicada não se edita.
- **Os portões não dependem de review**: imports por camada, leitura do ambiente, ORM proibido, regras do schema, documentação de toda rota, resposta só com status documentado e `telemetry` em todo `FastAPI(...)`. Uma regra nova ganha um cenário contra o código real e outro contra um exemplo errado.
- **Atualizar uma biblioteca**: suba o piso no `pyproject.toml`, rode `uv lock --upgrade-package <nome>` e `make check`, e atualize o [`stack.md`](stack.md).
- **Nome que vira rótulo** (nome de use case, de transação, de repositório, de query, de evento, de gateway) é contrato com os painéis: renomear quebra a série histórica.
- **O que o scaffold decidiu sem ADR** está na seção 7 do [`stack.md`](stack.md). Antes de tratar um desses itens como regra, registre a decisão.

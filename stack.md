# Stack do scaffold

Este documento lista as ferramentas, as bibliotecas com as versões e os design patterns que o scaffold usa, e diz de onde cada escolha veio. As versões "resolvidas" são as do `uv.lock` gerado em 2026-11-18, com a suíte passando (147 cenários sem Docker; mypy strict sem erro em 234 arquivos). O piso é o que o `pyproject.toml` exige.

## 1. Ferramentas

| Ferramenta | Versão | Para que serve | Onde está fixada |
|---|---|---|---|
| Python | 3.14 | linguagem; usa `type`, genéricos PEP 695 e `match` | `.python-version`, `requires-python` |
| uv | 0.11.2 | ambiente, lock e execução (`uv sync`, `uv run`) | backend de build `uv_build>=0.11.2,<0.12.0` |
| sqlc | 1.31.1 | gera o código Python de acesso a dados a partir do SQL | `SQLC_VERSION` no `Makefile` |
| sqlc-gen-python | 1.3.0 | plugin WASM do sqlc, com sha256 fixado | `sqlc.yaml` |
| GNU make | 4.x | atalhos da stack, da geração e dos portões | `Makefile` (usa `bash`) |
| Docker | 29.x | stack local e testes de integração (testcontainers) | `docker-compose.yml` |

## 2. Bibliotecas de runtime

| Biblioteca | Piso | Resolvida | Papel | Quem importa | Origem |
|---|---|---|---|---|---|
| fastapi | 0.142.2 | 0.165.0 | borda HTTP, Swagger e validação; `FastAPI(telemetry=...)` | `infrastructure/rest/`, `bootstrap/api.py` | ADR-011 |
| pydantic | (via fastapi) | 2.14.3 | schemas de entrada e saída, modo estrito | `infrastructure/rest/` | ADR-011 |
| starlette | (via fastapi) | 1.10.0 | `HTTPException` tratada pelo presenter | `infrastructure/rest/shared/` | ADR-011 |
| uvicorn | 0.54.0 | 0.54.0 | servidor ASGI, com `access_log=False` e `log_config=None` | `entrypoint/api.py` | ADR-012 |
| streamlit | 1.66.1 | 1.67.0 | borda visual | `infrastructure/streamlit/`, `entrypoint/streamlit_app.py` | pedido deste scaffold (sem ADR) |
| blinker | 1.9.0 | 1.9.0 | sinal in-process dos eventos de domínio | `infrastructure/events/` | ADR-001 |
| opentelemetry-api | 1.44 | 1.45.2 | métricas e spans pela API, providers injetados | `infrastructure/` | ADR-012 |
| opentelemetry-sdk | 1.44 | 1.45.2 | providers do processo, amostrador `ALWAYS_ON` | `bootstrap/telemetry.py` | ADR-012 |
| opentelemetry-exporter-otlp-proto-http | 1.44 | 1.45.2 | envio OTLP sobre HTTP (Prometheus e Jaeger) | `bootstrap/telemetry.py` | ADR-012 |
| sqlalchemy[asyncio] | 2.0.40 | 2.1.9 | só o Core assíncrono, sob o código do sqlc; ORM proibido | `infrastructure/persistence/` | ADR-003, ADR-004 |
| asyncpg | 0.31 | 0.32.0 | driver do Postgres | só `infrastructure/persistence/engine.py` | ADR-003 |
| aio-pika | 10.0.1 | 10.2.3 | Strategy RabbitMQ da outbox, com publisher confirms | `infrastructure/brokers/` | ADR-006 |
| croniter | 6.0 | 7.0.0 | calcula o próximo disparo do job; o laço é do projeto | `infrastructure/scheduling/`, `bootstrap/job_settings.py` | ADR-006 |

## 3. Bibliotecas de desenvolvimento

| Biblioteca | Piso | Resolvida | Papel | Origem |
|---|---|---|---|---|
| pytest | 9.1.1, abaixo de 10 | 9.2.0 | executor | ADR-010 |
| pytest-bdd | 9.0.0 | 9.0.1 | `.feature` em Gherkin (`# language: pt`) | ADR-010 |
| pytest-randomly | 5.0.0 | 5.1.0 | ordem aleatória: cenário dependente falha cedo | ADR-010 |
| pytest-cov | 7.0.0 | 7.1.0 | cobertura medida e reportada, sem mínimo | ADR-010 |
| mypy | 2.3.1 | 2.4.1 | `strict` em `src`, `tests` e `entrypoint` | ADR-007, ADR-008, ADR-010 |
| schemathesis | 4.0 | 4.33.4 | gera requisições do OpenAPI e acusa resposta fora do contrato | ADR-011 |
| hypothesis | (via schemathesis) | 6.170.15 | motor de geração do Schemathesis | ADR-011 |
| httpx2 | sem piso | 2.16.2 | cliente do `TestClient` do FastAPI | referências |
| testcontainers[postgres,rabbitmq] | 4.15 | 4.15.0 | Postgres, Flyway e RabbitMQ reais nos testes | ADR-010 |
| types-croniter | 6.2.4.20260711 | 6.2.4.20261118 | stubs do croniter para o mypy | referência da outbox |

## 4. Imagens da stack local

| Serviço | Imagem | Papel |
|---|---|---|
| postgres | `postgres:18.6-alpine` | banco (ADR-003) |
| flyway | `flyway/flyway:13.4-alpine` | aplica `migrations/` como job, também nos testes |
| rabbitmq | `rabbitmq:4.3-management-alpine` | broker da outbox; topologia em `config/rabbitmq/definitions.json` |
| prometheus | `prom/prometheus:v3.15.0` | recebe métricas por OTLP (`--web.enable-otlp-receiver`) |
| jaeger | `jaegertracing/jaeger:2.21.0` | recebe traces por OTLP; amostragem no destino (100% com erro, 5% do resto) |

## 5. Paradigmas e design patterns

| Pattern | O que resolve | Onde está no scaffold | Origem |
|---|---|---|---|
| Arquitetura hexagonal (portas e adaptadores) em camadas | o domínio e a aplicação não dependem de framework, banco nem broker | `domain/`, `applications/`, `infrastructure/`, `bootstrap/`, `entrypoint/`; cobrado em `tests/architecture/test_boundaries.py` | ADR-002, constituição |
| Bounded context em pacotes, um módulo por classe | "onde coloco este arquivo?" | `domain/bounded_context_example/{aggregates,entities,events,errors,value_objects,repositories}` | guidance `pacotes-de-bounded-context.md` |
| Aggregate Root | regras de negócio num lugar só; só a raiz muda as filhas | `Example` (`@dataclass(eq=False)`, fábrica `create`) | ADR-002, guidance `agregado-raiz.md` |
| Entity | identidade própria dentro do agregado | `ExampleItem` | guidance `entidade-filha.md` |
| Value Object | identificadores tipados e valores do domínio | `ExampleId` (`NewType`), `Category` (`StrEnum`), `OrderItem` | ADR-002 |
| Domain Event | o fato registrado pelo agregado, despachado depois do commit | `ExampleCreated`, `ExampleItemAdded`, `ExampleArchived` | ADR-001, guidance `evento-de-dominio.md` |
| Observer / pub-sub in-process | handlers isolados, falha medida e não propagada | `DomainEventDispatcher` e `DomainEventManager` sobre `blinker` | ADR-001, guidance `handler-de-evento-de-dominio.md` |
| Estado modelado por tipos (type-state) | transição proibida vira erro do mypy | `domain/bounded_context_order/aggregates/order.py`, `match` com `assert_never` | ADR-007, guidance `estado-modelado-por-tipos.md` |
| Command, Query e Use Case com 8 contratos | uma forma só de `execute`, conferida pelo mypy | `applications/shared/use_case.py`, `applications/usecases/` | ADR-008, guidance `commands-queries-e-use-cases.md` |
| DTO de saída | o agregado não sai do use case | `ExampleView.from_aggregate`, `ExampleSummary` | ADR-008 |
| Decorator (observação obrigatória) | log, métrica e span de todo use case num lugar | `Observed*UseCase`, `AsyncObserved*UseCase`, `UseCaseObserver` | ADR-008, ADR-012 |
| Unit of Work com `ContextVar` | transação nomeada, aninhamento que participa, toda transação medida | `domain/shared/persistence/unit_of_work.py` (porta), `infrastructure/persistence/unit_of_work.py` | ADR-004, ADR-005, guidance `unit-of-work-com-metricas.md` |
| Repository e leitor dedicado | gravar e reconstruir o agregado; ler DTO sem agregado | `IExampleRepository`, `IExampleReader`, `SqlExampleRepository`, `SqlExampleReader` | ADR-004, guidance `repositorio-sobre-querier-sqlc.md` |
| SQL-first com geração de código | query tipada, validada contra o schema; sem ORM | `queries/`, `migrations/`, `sqlc.yaml`, pastas `sqlc/` geradas | ADR-003, guidances `geracao-de-codigo-com-sqlc.md` e `migrations-e-queries-sql.md` |
| Mapper e Presenter nas periferias | cada fronteira traduz o seu modelo | `ExampleRequestMapper`, `ExamplePresenter`, `ExampleRowMapper`, mappers e presenters da CLI e da tela | ADR-009, guidance `mappers-e-presenters.md` |
| Anti-Corruption Layer | o vocabulário do fornecedor não entra no domínio | `CategoryPayloadMapper`, `ExternalCategoryGateway`, `UnmappedPayload` | ADR-009 |
| Transactional Outbox | sem dual write: estado e evento no mesmo commit | `OutboxWriter`, `OutboxDrainUseCase`, `SqlOutboxRepository`, `migrations/outbox/` | ADR-006, guidance `evento-de-integracao-pela-outbox.md` |
| Strategy (broker) | um publicador por broker, escolhido pelo carimbo | porta `IDispatcher`, `RabbitmqDispatcher` | ADR-006 |
| União selada | o resultado do envio não é booleano | `DispatchOutcome = Published \| TransientFailure \| PermanentFailure` | ADR-006 |
| Decorator de span (envoltório) | o span de envio fica fora da Strategy e da drenagem | `TracedDispatcher` | ADR-006 (emenda de 2026-10-15) |
| Composition root e injeção por construtor | um lugar só monta tudo; teste troca as portas | `bootstrap/composition.py` (`build_foundation`, `build_use_cases`) | ADR-008, ADR-012 |
| Configuração lida uma vez, interruptores estritos | só `true` e `false`; a recusa não repete o valor | `bootstrap/settings.py`, `bootstrap/job_settings.py` | ADR-011, ADR-012 |
| Porta de métricas com dois adaptadores | métricas desligadas vão para o log, e não somem | `build_metrics_adapters` | ADR-005, ADR-012 |
| Log estruturado com correlação pelo trace | linha JSON com `trace_id`; mensagem da exceção nunca escrita | `JsonLogFormatter`, `configure_logging` | ADR-012, guidance `telemetria-com-opentelemetry.md` |
| API documentada e validada | Swagger sai do código; teste cobra todas as rotas | `RequestSchema`, `ErrorPresenter.documented_errors`, `tests/support/openapi_rules.py` | ADR-011, guidance `api-rest-documentada-e-validada.md` |
| BDD com `.feature` | o cenário é o teste, na língua do negócio | `tests/features/**.feature`, um `test_*.py` por feature | ADR-010, guidance `testes-com-bdd.md` |
| Teste de contrato fake e real | o fake só vale porque passa pelo mesmo cenário | `@contract`, fixture `backend` (fake e postgres) | ADR-010, guidance `testes-de-contrato-e-integracao-com-bdd.md` |
| Portões de arquitetura | regra que não depende de review | `tests/architecture/` (imports, ambiente, ORM, schema) | ADR-003, ADR-012 |
| Ponte de event loop | borda síncrona chamando use case assíncrono sem trocar de loop | `bootstrap/background_loop.py` | escolha deste scaffold (sem ADR) |

## 6. Variáveis de ambiente

| Variável | Processos | Obrigatória | Sem a variável | Efeito |
|---|---|---|---|---|
| `OTEL_SERVICE_NAME` | todos | sim | recusa o boot | nome do serviço em todo sinal |
| `DATABASE_URL` | todos | sim | recusa o boot | só `postgresql://`, sem driver |
| `OUTBOX_DISPATCHER` | todos | sim | recusa o boot | carimbo da outbox; aceita `rabbitmq` |
| `LOG_DEBUG` | todos | não | `false` | `false`: só WARNING e ERROR; `true`: tudo, a partir de DEBUG |
| `TELEMETRY_METRICS_ENABLED` | todos | não | `true` | desligada, as medições vão para o log, em DEBUG |
| `TELEMETRY_TRACES_ENABLED` | todos | não | `true` | desligada, os spans seguem criados (id do trace no log), sem envio |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | todos | não | `http://localhost:4318` | endereço base dos dois sinais |
| `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT` e `..._TRACES_ENDPOINT` | todos | não | o endereço base | endereço completo de cada sinal |
| `API_EXPOSE_DOCS` | API | não | `false` | serve `/docs` e `/openapi.json`; as rotas são documentadas sempre |
| `RABBITMQ_URL` | job | sim | recusa o boot | `amqp://` ou `amqps://` |
| `OUTBOX_CRON_SCHEDULE` | job | não | `* * * * *` | cron de cinco campos, em UTC |
| `OUTBOX_BATCH_SIZE` | job | não | `1000` | mensagens por ciclo |
| `OUTBOX_RETRY_COUNTDOWN` | job | não | `30` | segundos até a nova tentativa |

## 7. Escolhas do scaffold que não têm ADR

Os itens abaixo foram decididos para o scaffold existir e rodar, e nenhuma ADR os cobre. Ficam registrados como pendentes de decisão; nenhum foi tratado como aprovado.

1. **Streamlit como borda visual**, com o event loop de fundo (`BackgroundLoop`) para manter o pool do banco num loop só.
2. **CLI com `argparse`** (biblioteca padrão) e os códigos de saída 0 (sucesso), 1 (configuração recusada ou defeito), 2 (argumento inválido) e 3 (pedido recusado por uma regra).
3. **`LOG_DEBUG` booleano**, como pedido. O módulo de backend do monorepo usa `LOG_LEVEL` com quatro níveis; as duas formas concordam no padrão WARNING e nos registros de rotina em DEBUG.
4. **Health check `GET /api/v1/health/check`** só de liveness: responde 200 sem consultar dependências e sem use case. A ADR-016 decide `/live` e `/ready` com probes em paralelo; alinhar as duas formas é uma decisão em aberto.
5. **Prefixo `/api/v1`** em todas as rotas.
6. **Só a Strategy RabbitMQ.** A referência da outbox tem também a do SNS; uma Strategy nova entra pelos passos do README.
7. **Topologia do RabbitMQ local** carregada de `config/rabbitmq/definitions.json` (usuário `app`, exchange `example`, fila `example.audit`).
8. **Duas extensões sobre o `ErrorPresenter` da referência**: `knows(error)`, para a montagem escolher o presenter quando houver mais de um agregado, e a junção das descrições quando dois erros da mesma rota têm o mesmo status (os 409 da criação).
9. **Nome do pacote `scafold`**, com a grafia do pedido. Para usar em outro repositório, o README mostra a troca.
10. **`API_EXPOSE_DOCS=true` no `.env.example`**, para o Swagger aparecer no uso local. O padrão da variável continua desligado.
11. **Versões resolvidas mais novas que as das referências** (por exemplo FastAPI 0.165.0 contra 0.142.2, SQLAlchemy 2.1.9 contra 2.0.54, croniter 7.0.0 contra 6.2.4). A suíte passou com elas; os pisos do `pyproject.toml` são os das referências.

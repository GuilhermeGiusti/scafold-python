---
title: Telemetria com OpenTelemetry
version: 1.0.0
---

# Telemetria com OpenTelemetry

## Propósito

Depois de ler, você saberá montar a telemetria de um processo: criar os providers de métricas e de traces que enviam por OTLP, entregá-los ao FastAPI, ao observador de use case, à Unit of Work e ao envoltório da outbox, escolher os adaptadores de métricas, configurar o log estruturado com o id do trace e abrir um span novo seguindo o contrato dos que já existem. A referência é [`bootstrap/telemetry.py`](../scafold/src/scafold/bootstrap/telemetry.py), [`bootstrap/composition.py`](../scafold/src/scafold/bootstrap/composition.py) e [`infrastructure/observability/`](../scafold/src/scafold/infrastructure/observability/).

## Problema que resolve

As armadilhas abaixo estão descritas no código da referência:

- O FastAPI abre um canal de envio por conta própria se encontrar uma variável `OTEL_EXPORTER_OTLP_*` no ambiente e o app for criado sem o argumento `telemetry`.
- Desligar os traces apagando os spans tira o id do trace do log, que é o identificador de correlação.
- O span grava a mensagem da exceção se ninguém impedir, e ela costuma trazer o dado recusado ou o SQL com os parâmetros.
- Valor livre em rótulo cria uma série por valor.
- Cada ponto buscando o provider global não pode ser testado nem desligado em conjunto.

## Por que foi criado

Pedido de 2026-11-18: guidances que ensinem a implementar seguindo o projeto de referência `../scafold`, para usar em outros repositórios. A decisão que o sustenta é a ADR-012 (Observabilidade dos módulos de backend com OpenTelemetry).

## Como implementar

### 1. As dependências

O processo declara `opentelemetry-sdk` e `opentelemetry-exporter-otlp-proto-http` (o Prometheus só recebe OTLP por HTTP); o código que só mede ou abre span usa a API. Nenhuma biblioteca de instrumentação automática entra. Veja [`pyproject.toml`](../scafold/pyproject.toml).

### 2. Monte os providers uma vez

`build_telemetry` recebe a configuração (o protocolo `TelemetrySettings`, cumprido por `Settings` e `JobSettings`) e devolve um `Telemetry` com os dois providers, ambos com o `service.name`:

- métricas desligadas: `meter_provider` é `None`, e a montagem troca de adaptador;
- traces desligados: o provider existe sem exportador, e os spans seguem dando o id do trace ao log;
- amostrador `ALWAYS_ON`: quem decide o que guardar é o destino;
- `Telemetry.shutdown` envia o que falta, num `finally` do ponto de entrada. Montar não conecta.

As variáveis que ligam e desligam cada sinal estão em [Configuração pelo ambiente e nível do log](configuracao-pelo-ambiente.md).

### 3. Entregue os providers ao FastAPI

Todo app é criado com `FastAPI(telemetry=framework_telemetry(telemetry))`, em [`bootstrap/api.py`](../scafold/src/scafold/bootstrap/api.py). `framework_telemetry` entrega os dois providers, desliga as métricas do framework junto com as do processo, desliga o sinal de logs dele e a leitura automática do ambiente. A borda HTTP não tem middleware do projeto: o span da requisição e a duração são do framework.

### 4. Escolha os adaptadores de métricas

Cada ponto que mede fala com uma porta, e cada porta tem dois adaptadores: o OpenTelemetry e o de log, que escreve a medição em DEBUG no formato do Prometheus. `build_metrics_adapters` entrega um conjunto ou outro conforme o `meter_provider`, num `MetricsAdapters` com `use_case`, `persistence`, `domain_events`, `translation` e `outbox`. Desligar as métricas não apaga a medição: ela vai para o log. Uma porta nova entra em `MetricsAdapters` com os dois adaptadores.

| Porta | Adaptadores | Instrumentos |
|---|---|---|
| `IUseCaseMetrics` | `OpenTelemetryUseCaseMetrics`, `LoggingUseCaseMetrics` | `use_case.executions`, `use_case.duration` |
| `IPersistenceMetrics` | `OpenTelemetryPersistenceMetrics`, `LoggingPersistenceMetrics` | `db.transactions`, `db.transaction.duration`, `db.transactions.in_flight`, `db.query.duration` |
| `IDomainEventMetrics` | `OpenTelemetryDomainEventMetrics`, `LoggingDomainEventMetrics` | `domain.events.published`, `domain.event.handlers`, `domain.event.handler.duration` |
| `ITranslationErrorMetrics` | `OpenTelemetryTranslationErrorMetrics`, `LoggingTranslationErrorMetrics` | `external.translation.errors` |
| `IOutboxMetrics` | `OpenTelemetryOutboxMetrics`, `LoggingOutboxMetrics` | `outbox.dispatched`, `outbox.dead.messages`, `events.published` e os gauges do backlog e da duração |

Os histogramas recebem limites em segundos (`DURATION_BUCKETS_SECONDS`) em `explicit_bucket_boundaries_advisory`.

### 5. Entregue o mesmo `TracerProvider` a quem abre span

| Quem abre | Span | Como recebe o provider |
|---|---|---|
| FastAPI | `<método> <rota>` | `framework_telemetry` |
| `UseCaseObserver` | `use_case <nome>` | construtor, em `build_foundation` |
| `UnitOfWork` e o ouvinte de queries | `db.transaction <nome>`, `db.query <query>` | `open_persistence` |
| `TracedDispatcher` | `outbox.dispatch <evento>` | construtor, em `build_outbox_job` |

Cada span fica corrente enquanto o trecho dele roda, então uma requisição vira um trace só: rota, use case, transação e query. Sem provider, o ponto não cria span e continua medindo; o padrão é no-op, nunca o global.

### 6. Abra um span novo seguindo o contrato

Siga `UseCaseObserver.observe`, em [`use_case_observer.py`](../scafold/src/scafold/infrastructure/observability/use_case_observer.py), e [`persistence_spans.py`](../scafold/src/scafold/infrastructure/persistence/persistence_spans.py):

- o provider entra pelo construtor, com `None` virando no-op (veja `persistence_tracer`);
- o escopo de instrumentação é o mesmo das métricas daquele ponto;
- o nome é um prefixo fixo mais um nome do catálogo, nunca id, caminho ou nome de classe;
- os atributos são os rótulos da métrica correspondente, declarados numa constante (`USE_CASE_SPAN_ATTRIBUTES`, `TRANSACTION_SPAN_ATTRIBUTES`, `DISPATCH_SPAN_ATTRIBUTES`);
- abra com `record_exception=False` e `set_status_on_exception=False`, e marque a falha à mão só com o nome da classe (`mark_failed`);
- qualquer exceção marca o span como erro;
- use `start_as_current_span` quando o trecho chama outro que abre span, e `start_span` quando não chama.

### 7. Configure o log estruturado

`configure_logging`, em [`json_log_formatter.py`](../scafold/src/scafold/infrastructure/observability/json_log_formatter.py), põe o `JsonLogFormatter` no logger raiz, uma vez, com o nível da configuração. Toda linha é um JSON com `LOG_FIELDS` (`timestamp`, `level`, `logger`, `message`, `service`, `trace_id`, `span_id`); uma exceção acrescenta `ERROR_FIELDS` (`error_type` e `stack`), e a mensagem dela nunca é escrita. O `trace_id` é o identificador de correlação, e não há `correlation_id` à parte. O log de acesso do servidor fica desligado (`access_log=False`) e o servidor não troca o formatador (`log_config=None`), em [`entrypoint/api.py`](../scafold/entrypoint/api.py).

### 8. Não ponha dado pessoal nos sinais

Métrica, span e log não levam cabeçalho, corpo, parâmetro de SQL nem a mensagem de uma exceção. Ao acrescentar uma biblioteca, confira o que ela escreve no log: o formatador não limpa a mensagem que outra biblioteca montou.

### 9. Veja os sinais na stack local

O [`docker-compose.yml`](../scafold/docker-compose.yml) sobe o Prometheus com `--web.enable-otlp-receiver` e o Jaeger com a amostragem no destino ([`config/jaeger.yaml`](../scafold/config/jaeger.yaml): 100% dos traces com erro, 5% do resto). Os endereços de cada sinal estão no [`.env.example`](../scafold/.env.example).

### 10. Testar

- Os spans de use case, com `InMemorySpanExporter` (fixtures `spans` e `tracer_provider` em [`tests/conftest.py`](../scafold/tests/conftest.py)), em [`use_case_observation.feature`](../scafold/tests/features/infrastructure/use_case_observation.feature).
- Os adaptadores, com `InMemoryMetricReader`, em [`metrics_adapters.feature`](../scafold/tests/features/infrastructure/metrics_adapters.feature).
- O `telemetry` em todo `FastAPI(...)`, em [`framework_telemetry.feature`](../scafold/tests/features/rest/framework_telemetry.feature).
- O log JSON sem a mensagem da exceção, em [`log_level.feature`](../scafold/tests/features/bootstrap/log_level.feature).

## Quando não se aplica

O envio dos logs a um destino central, dashboards, alertas, retenção no Jaeger e telemetria de frontend não são cobertos.

## Guidances relacionados

- [Configuração pelo ambiente e nível do log](configuracao-pelo-ambiente.md) (v1.0.0): as variáveis que ligam cada sinal e o nível do log.
- [Commands, queries e use cases](commands-queries-e-use-cases.md) (v1.0.0): o decorator que mede e abre o span do use case.
- [Unit of Work com métricas](unit-of-work-com-metricas.md) (v1.0.0): as séries e os spans de transação e query.
- [Evento de integração pela outbox](evento-de-integracao-pela-outbox.md) (v1.0.0): o span de envio que continua o trace do produtor.

## Change log

| Versão | Data       | Pessoa           | Motivo                                                                                   |
|--------|------------|------------------|------------------------------------------------------------------------------------------|
| 1.0.0  | 2026-11-18 | Guilherme Giusti | Criação: ensinar a montar métricas, traces e log estruturado com o scaffold como referência |

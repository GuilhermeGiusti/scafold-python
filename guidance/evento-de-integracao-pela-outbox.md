---
title: Evento de integração pela outbox
version: 1.0.0
---

# Evento de integração pela outbox

## Propósito

Depois de ler, você saberá:

- gravar um evento de integração na outbox, dentro da transação que grava a mudança de estado, com o gravador carimbado pela montagem;
- escrever uma Strategy de broker que publica e relata o resultado sem lançar exceção;
- abrir o span de envio por um envoltório da Strategy;
- subir o job que drena a fila por cron;
- testar cada parte com fakes e com Postgres e RabbitMQ reais.

A referência é [`domain/outbox/`](../scafold/src/scafold/domain/outbox/), [`infrastructure/events/outbox_writer.py`](../scafold/src/scafold/infrastructure/events/outbox_writer.py), [`applications/usecases/outbox_drain_use_case.py`](../scafold/src/scafold/applications/usecases/outbox_drain_use_case.py) e [`entrypoint/outbox_job.py`](../scafold/entrypoint/outbox_job.py).

## Problema que resolve

O dual write. Se o código que muda o estado também publica no broker, uma falha entre as duas operações deixa o dado gravado sem a mensagem, ou a mensagem publicada sem o dado. Com a outbox, quem muda o estado só insere uma linha numa tabela, na mesma transação, e um job separado publica, podendo tentar de novo sem perder nada.

## Por que foi criado

Pedido de 2026-11-18: guidances que ensinem a implementar seguindo o projeto de referência `../scafold`, para usar em outros repositórios. A decisão que o sustenta é a ADR-006 (Outbox transaction para eventos de integração), com a emenda de 2026-10-15 que tira o span de envio da drenagem; a ADR-017 (API e job da outbox no mesmo módulo) decide os dois pontos de entrada lado a lado.

## Como implementar

### 1. Descreva o evento com `IntegrationEvent`

O value object, em [`integration_event.py`](../scafold/src/scafold/domain/outbox/value_objects/integration_event.py), traz `destination` (nome **lógico** do alvo, nunca exchange, tópico ou ARN), `event_type`, `event_version`, `payload`, `aggregate_type`, `aggregate_id` e a `routing_key` opcional. `validate` recusa o evento incompleto antes de qualquer conexão, com `InvalidIntegrationEvent`, que nomeia o campo e nunca repete o valor. O contrato do evento que um use case produz fica numa função dele: `example_created_event`, em [`create_example_use_case.py`](../scafold/src/scafold/applications/usecases/create_example_use_case.py).

### 2. Grave dentro da transação que grava o estado

O use case chama `writer.write(event)` **dentro** do bloco `unit_of_work.transaction(...)` que grava o agregado (veja `CreateExampleUseCase.execute`). O gravador cumpre a porta `IIntegrationWriter`, em [`integration_writer.py`](../scafold/src/scafold/domain/outbox/ports/integration_writer.py), e não recebe conexão: pede `write_querier("outbox_writer")` à Unit of Work, que recusa fora da transação. A ordem das recusas em `OutboxWriter.write`:

1. o evento incompleto (`validate`);
2. a gravação sem span corrente (`MissingTraceContext`): o `correlation_id` é o id do trace, e o `traceparent` sai do mesmo span. O decorator do use case sempre abre um;
3. a gravação fora de transação, recusada pela própria Unit of Work.

O gravador grava a linha em `outbox_message` e os dados de envio congelados na tabela do broker (`insert_outbox_message_rabbitmq`, com a routing key ou o tipo do evento) e conta `events.published`. Ele é montado com o carimbo de `OUTBOX_DISPATCHER`, obrigatório: `UnknownDispatcher` recusa carimbo fora de `KNOWN_DISPATCHERS`, em [`dispatchers.py`](../scafold/src/scafold/domain/outbox/dispatchers.py).

**O que não fazer:** publicar no broker de dentro do código que muda o estado, antes ou depois do commit.

### 3. Escreva a Strategy cumprindo `IDispatcher`

A porta, em [`ports/dispatcher.py`](../scafold/src/scafold/domain/outbox/ports/dispatcher.py), tem `name` e `dispatch(message)`. A Strategy publica e relata, e só isso: não lança, não conta tentativas, não grava no banco e não abre span. O retorno é a união selada `DispatchOutcome` (`Published | TransientFailure | PermanentFailure`), em [`dispatch_outcome.py`](../scafold/src/scafold/domain/outbox/value_objects/dispatch_outcome.py).

Veja `RabbitmqDispatcher`, em [`rabbitmq_dispatcher.py`](../scafold/src/scafold/infrastructure/brokers/rabbitmq_dispatcher.py): publisher confirms e `on_return_raises=True` no canal, `mandatory=True` na publicação, confirmação com prazo (`CONFIRM_TIMEOUT_SECONDS`) e exchange declarada de forma passiva. Cada exceção vira um dos três casos: `_PERMANENT` primeiro, `ChannelClosed` com `ACCESS_REFUSED` como permanente, `_TRANSIENT` e qualquer outra exceção como transitória. O detalhe (`_describe`) vai só para o histórico, com até 500 caracteres e nunca o payload. `start` conecta (broker fora no boot derruba o processo) e `close` desconecta; os dois ficam fora da porta, porque só o job os chama.

Uma Strategy nova também entra em `KNOWN_DISPATCHERS`, numa migration nova com o carimbo no `CHECK` e a tabela de dados de envio, e na montagem do job.

### 4. Abra o span de envio pelo envoltório

`TracedDispatcher`, em [`traced_dispatcher.py`](../scafold/src/scafold/infrastructure/observability/traced_dispatcher.py), cumpre `IDispatcher`, envolve a Strategy e abre `outbox.dispatch <evento>`, continuando o trace do produtor a partir do `traceparent` gravado na linha. Os atributos são os de `DISPATCH_SPAN_ATTRIBUTES`; numa falha, o status leva só o tipo do resultado (`transient_error`, `permanent_error`), nunca o detalhe.

### 5. Deixe a decisão para a drenagem

`OutboxDrainUseCase`, um `AsyncNullaryUseCase[DrainResult]`, processa até `batch_size` mensagens, cada uma numa transação `outbox_drain` própria: reivindica a linha (`FOR UPDATE OF m SKIP LOCKED`, em [`queries/outbox/outbox.sql`](../scafold/queries/outbox/outbox.sql)), chama o dispatcher e aplica o resultado com `match` terminando em `assert_never` (veja `_apply`):

- `Published` marca `PUBLISHED`;
- `PermanentFailure` marca `DEAD` na hora e conta a morte com o motivo `permanent`;
- `TransientFailure` registra a falha e reagenda até `MAX_ATTEMPTS` (5), e então marca `DEAD` com o motivo `attempts_exhausted`.

Fila vazia é estado normal: `NoPendingMessage` é tratado dentro do bloco, e a transação commita vazia. A parada é conferida antes de cada reivindicação. No fim do ciclo, o backlog de todos os carimbos, semeado com zero, e a duração vão para a porta `IOutboxMetrics`, em [`applications/ports/outbox_metrics.py`](../scafold/src/scafold/applications/ports/outbox_metrics.py). O repositório da fila é `SqlOutboxRepository`, em [`sql_outbox_repository.py`](../scafold/src/scafold/infrastructure/persistence/outbox/sql_outbox_repository.py).

### 6. Suba o job

O job é um processo próprio. `build_outbox_job`, em [`bootstrap/outbox_job.py`](../scafold/src/scafold/bootstrap/outbox_job.py), monta a camada de dados, o observador, a Strategy com o envoltório, a drenagem (envolvida pelo decorator, com o rótulo `outbox_drain`) e o `CronScheduler`, em [`cron_scheduler.py`](../scafold/src/scafold/infrastructure/scheduling/cron_scheduler.py). O agendador espera o primeiro disparo (não drena no boot), roda um ciclo por vez, pula com WARNING o disparo que caiu durante um ciclo e registra em ERROR o ciclo que falhou sem derrubar o job.

`entrypoint/outbox_job.py` segue a ordem: configuração (`JobSettings`), log e telemetria, `broker.start()`, o laço até o sinal de encerramento, e `close` num `finally`. As variáveis estão em [`job_settings.py`](../scafold/src/scafold/bootstrap/job_settings.py) e no [`.env.example`](../scafold/.env.example). Na stack local, a topologia do RabbitMQ vem de [`config/rabbitmq/definitions.json`](../scafold/config/rabbitmq/definitions.json).

### 7. Testar

- A política da drenagem, com o fake `ScriptedDispatcher` e a fila `InMemoryOutboxRepository`, em [`outbox_drain.feature`](../scafold/tests/features/applications/outbox_drain.feature).
- O span de envio, em [`traced_dispatcher.feature`](../scafold/tests/features/infrastructure/traced_dispatcher.feature).
- O agendador, com relógio de mentira, em [`cron_scheduler.feature`](../scafold/tests/features/infrastructure/cron_scheduler.feature).
- Contra Postgres real (`@integration`): o rollback que não deixa nem o estado nem a mensagem, o carimbo com o id do trace e a drenagem que publica, em [`outbox_persistence.feature`](../scafold/tests/features/infrastructure/outbox_persistence.feature).
- Contra RabbitMQ real (`@integration`): publicada e destino inexistente como falha permanente, em [`rabbitmq_dispatcher.feature`](../scafold/tests/features/infrastructure/rabbitmq_dispatcher.feature).

## Quando não se aplica

O evento que só aciona handlers no mesmo processo é evento de domínio: siga [Evento de domínio](evento-de-dominio.md). A outbox é para o que sai do processo.

## Guidances relacionados

- [Unit of Work com métricas](unit-of-work-com-metricas.md) (v1.0.0): a transação dentro da qual o evento é gravado.
- [Commands, queries e use cases](commands-queries-e-use-cases.md) (v1.0.0): o use case que grava e o contrato sem input da drenagem.
- [Telemetria com OpenTelemetry](telemetria-com-opentelemetry.md) (v1.0.0): o span de onde saem o `correlation_id` e o `traceparent`.
- [Migrations e queries SQL](migrations-e-queries-sql.md) (v1.0.0): a migration e as queries da outbox.

## Change log

| Versão | Data       | Pessoa           | Motivo                                                                                   |
|--------|------------|------------------|------------------------------------------------------------------------------------------|
| 1.0.0  | 2026-11-18 | Guilherme Giusti | Criação: ensinar a gravar, publicar e drenar eventos de integração pela outbox com o scaffold como referência |

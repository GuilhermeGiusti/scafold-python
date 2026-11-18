---
title: Handler de evento de domínio
version: 1.0.0
---

# Handler de evento de domínio

## Propósito

Depois de ler, você saberá escrever um handler que reage a eventos de domínio, registrá-lo no `DomainEventManager` e testar o despacho. O guia cobre o handler de um evento, o de todos os eventos e o que o manager faz quando um handler falha. A referência é [`applications/handlers/`](../scafold/src/scafold/applications/handlers/) e a montagem em `build_event_manager`, em [`composition.py`](../scafold/src/scafold/bootstrap/composition.py).

## Problema que resolve

As armadilhas abaixo estão descritas nas docstrings da referência:

- O handler roda depois do commit, então a falha dele não desfaz nada. Quem a trata é o manager: captura, registra no log e na métrica com `status="error"` e segue para o próximo handler. Um `try/except` dentro do handler faria a métrica registrar `ok` e esconderia o erro.
- O sinal `blinker` guarda só uma referência fraca ao manager. Sem uma referência forte, o manager é coletado e os handlers deixam de receber eventos.
- O sinal é global por nome: handlers registrados num teste vazam para o próximo se o manager não for limpo.

## Por que foi criado

Pedido de 2026-11-18: guidances que ensinem a implementar seguindo o projeto de referência `../scafold`, para usar em outros repositórios. A decisão que o sustenta é a ADR-001 (Despacho in-process de eventos de domínio com blinker).

## Como implementar

### 1. O contrato

O handler cumpre `IDomainEventHandler`, em [`event_base.py`](../scafold/src/scafold/domain/shared/events/event_base.py), por estrutura, sem herança, com dois métodos: `listener_to()`, que devolve as classes escutadas e é lido uma vez no registro, e `handle(event)`. O manager entrega o evento quando `isinstance(event, <classe escutada>)` é verdadeiro.

### 2. Handler de um evento

Fica em `applications/handlers/<evento>_handler.py`. A ação de saída chega pelo construtor como função, e o handler não conhece o canal. `handle` confere o tipo do evento (o que também estreita o tipo para o mypy) e chama a saída, usando os campos do evento sem reabrir o agregado. Não há `try/except`. Veja `ExampleCreatedHandler`, em [`example_created_handler.py`](../scafold/src/scafold/applications/handlers/example_created_handler.py).

Para vários eventos, `listener_to` devolve várias classes e `handle` escolhe o caminho com `match`.

### 3. Handler de todos os eventos

Se `listener_to` devolver `[IDomainEvent]`, o handler recebe os eventos de todos os contextos, porque `IDomainEvent` é `runtime_checkable`. Ele não interpreta o evento: repassa `to_json()` para a saída. Veja `AllEventsHandler`, em [`all_events_handler.py`](../scafold/src/scafold/applications/handlers/all_events_handler.py).

### 4. Registrar no manager

Todos os handlers são registrados numa única instância de `DomainEventManager`, em [`event_manager.py`](../scafold/src/scafold/infrastructure/events/event_manager.py), numa chamada a `register`, com a saída de cada um decidida na montagem. Veja `build_event_manager`. Os handlers de um mesmo evento rodam na ordem de registro, e registrar duas vezes não tem efeito.

Guarde o manager em algo que viva o processo inteiro: na referência, o campo `event_manager` da `Foundation`. O dispatcher que os use cases recebem é `DomainEventDispatcher`, em [`event_dispatcher.py`](../scafold/src/scafold/infrastructure/events/event_dispatcher.py), sobre o mesmo sinal.

### 5. Falhas e métricas

`DomainEventManager._deliver` mede cada `handle`, captura qualquer `Exception`, registra com `log.exception` e chama `metrics.handled(...)` com `status` igual a `"ok"` ou `"error"`. A porta é `IDomainEventMetrics`, em [`event_metrics.py`](../scafold/src/scafold/infrastructure/events/event_metrics.py):

| Métrica | Rótulos | Emitida por |
|---|---|---|
| `domain_events_published_total` | `event_name` | `DomainEventDispatcher.dispatch` |
| `domain_event_handlers_total` | `event_name`, `handler`, `status` | `DomainEventManager`, ao fim de cada `handle` |
| `domain_event_handler_duration_seconds` | `event_name`, `handler` | `DomainEventManager`, ao fim de cada `handle` |

Os dois adaptadores ficam na mesma pasta: `OpenTelemetryDomainEventMetrics` e `LoggingDomainEventMetrics`, que escreve em DEBUG. Qual o processo recebe é decidido em `build_metrics_adapters` (veja [Telemetria com OpenTelemetry](telemetria-com-opentelemetry.md)).

### 6. Testar e isolar

O despacho e a falha isolada estão em [`domain_events.feature`](../scafold/tests/features/infrastructure/domain_events.feature), com os steps em [`test_domain_events.py`](../scafold/tests/infrastructure/test_domain_events.py) e o dublê `RecordingDomainEventMetrics` em [`fakes.py`](../scafold/tests/support/fakes.py). A fixture `autouse` `_isolated_domain_signal`, em [`tests/conftest.py`](../scafold/tests/conftest.py), limpa o sinal ao fim de cada cenário. Nos testes de use case, o dispatcher é o dublê `RecordingDomainEventDispatcher`.

## Guidances relacionados

- [Evento de domínio](evento-de-dominio.md) (v1.0.0): as classes que o handler escuta.
- [Commands, queries e use cases](commands-queries-e-use-cases.md) (v1.0.0): onde o use case recolhe e despacha os eventos.
- [Telemetria com OpenTelemetry](telemetria-com-opentelemetry.md) (v1.0.0): como a montagem escolhe o adaptador de métricas.

## Change log

| Versão | Data       | Pessoa           | Motivo                                                                                   |
|--------|------------|------------------|------------------------------------------------------------------------------------------|
| 1.0.0  | 2026-11-18 | Guilherme Giusti | Criação: ensinar a escrever e registrar handlers de eventos com o scaffold como referência |

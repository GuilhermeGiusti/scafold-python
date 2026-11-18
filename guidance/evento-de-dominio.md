---
title: Evento de domínio
version: 1.0.0
---

# Evento de domínio

## Propósito

Depois de ler, você saberá escrever a classe de um evento de domínio e registrá-lo de dentro do agregado. O guia cobre a base `DomainEvent`, os campos, `versioning`, `name` e `to_json`, e a ordem em que o agregado chama `add_event`. A referência é [`domain/shared/events/`](../scafold/src/scafold/domain/shared/events/) e [`domain/bounded_context_example/events/`](../scafold/src/scafold/domain/bounded_context_example/events/).

## Problema que resolve

As armadilhas abaixo estão descritas nas docstrings da referência:

- Os eventos ficam guardados num `set`, então precisam ser hashable. Sem `eq=False`, `set.add` levanta `TypeError`.
- Sem `occurred_on` vindo da base, cada evento teria de preencher o próprio instante.
- Se faltar `versioning`, `name` ou `to_json`, o mypy recusa a subclasse.
- `name()` é rótulo de métrica: renomear um evento quebra a série histórica.

## Por que foi criado

Pedido de 2026-11-18: guidances que ensinem a implementar seguindo o projeto de referência `../scafold`, para usar em outros repositórios. As decisões que o sustentam são a ADR-002 (Domain Driven Design nos módulos backend) e a ADR-001 (Despacho in-process de eventos de domínio com blinker).

## Como implementar

### 1. O contrato e a base

Todo evento cumpre `IDomainEvent`, em [`event_base.py`](../scafold/src/scafold/domain/shared/events/event_base.py), estendendo `DomainEvent`, em [`domain_event.py`](../scafold/src/scafold/domain/shared/events/domain_event.py). A base é um `@dataclass(eq=False, kw_only=True)` e fornece `occurred_on` (epoch UTC) como argumento só por nome, para não atrapalhar a ordem dos campos das subclasses. Você não altera essas classes.

### 2. Escrever a classe do evento

O evento fica em `events/<agregado>_<fato>.py` do contexto, com o nome no passado (`Created`, `ItemAdded`, `Archived`). Os campos carregam o id do agregado e tudo de que os handlers precisam, para que eles não reabram o agregado. A classe é um `@dataclass(eq=False)`. A referência é `ExampleItemAdded`, em [`example_item_added.py`](../scafold/src/scafold/domain/bounded_context_example/events/example_item_added.py), com `aggregate_id`, `item_id` e `item_name`.

Os três métodos seguem regras fixas:

- `versioning()` devolve a versão do formato, começando em `"1"`.
- `name()` devolve um nome estável `<contexto>.<agregado>.<fato>`, em snake_case, como `bounded_context_example.example.item_added`. É o rótulo `event_name` das métricas de publicação e de tratamento.
- `to_json()` devolve `versioning`, `name`, todos os campos e `occurred_on`. Ids viram `str`, e valores do domínio viram o valor serializável (veja `category.value` em `ExampleCreated`).

Um evento sem dados além do id carrega só `aggregate_id`. Veja `ExampleArchived`, em [`example_archived.py`](../scafold/src/scafold/domain/bounded_context_example/events/example_archived.py).

### 3. Registrar o evento de dentro do agregado

Só o agregado cria o evento, e só depois de validar a regra e mudar o estado, com `self.add_event(...)`. Veja `Example.archive`, em [`example.py`](../scafold/src/scafold/domain/bounded_context_example/aggregates/example.py).

### 4. Recolher e despachar

Os eventos ficam no agregado até o use case recolhê-los com `dispatcher.collect(aggregate)`, dentro da transação, e despachá-los com `dispatcher.dispatch(events)`, depois do commit. Veja `CreateExampleUseCase.execute`, em [`create_example_use_case.py`](../scafold/src/scafold/applications/usecases/create_example_use_case.py). Quem trata o evento está em [Handler de evento de domínio](handler-de-evento-de-dominio.md).

## Quando não se aplica

O evento que sai do processo, para outro módulo ou serviço, não é evento de domínio: é evento de integração, gravado na outbox. Siga [Evento de integração pela outbox](evento-de-integracao-pela-outbox.md).

## Guidances relacionados

- [Agregado raiz](agregado-raiz.md) (v1.0.0): as operações que registram eventos.
- [Handler de evento de domínio](handler-de-evento-de-dominio.md) (v1.0.0): quem reage ao evento.
- [Pacotes e camadas de um módulo](pacotes-e-camadas-do-modulo.md) (v1.0.0): onde fica o módulo do evento.

## Change log

| Versão | Data       | Pessoa           | Motivo                                                                                   |
|--------|------------|------------------|------------------------------------------------------------------------------------------|
| 1.0.0  | 2026-11-18 | Guilherme Giusti | Criação: ensinar a escrever e registrar eventos de domínio com o scaffold como referência |

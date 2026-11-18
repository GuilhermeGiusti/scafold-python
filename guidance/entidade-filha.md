---
title: Entidade filha de um agregado
version: 1.0.0
---

# Entidade filha de um agregado

## Propósito

Depois de ler, você saberá escrever uma entidade que vive dentro de um agregado, com identidade própria, criada e alterada só pela raiz, e o método da raiz que a cria. A referência é `ExampleItem`, em [`entities/example_item.py`](../scafold/src/scafold/domain/bounded_context_example/entities/example_item.py), e `Example.add_item`.

## Problema que resolve

Se a entidade for criada ou alterada fora da raiz, as regras do agregado deixam de valer: na referência, o nome único entre os itens e a recusa de item num Example arquivado.

## Por que foi criado

Pedido de 2026-11-18: guidances que ensinem a implementar seguindo o projeto de referência `../scafold`, para usar em outros repositórios. A decisão que o sustenta é a ADR-002 (Domain Driven Design nos módulos backend).

## Como implementar

### 1. Identificador da entidade

Como o agregado, a entidade tem um `NewType` sobre `UUID` em `value_objects/`. Veja `ExampleItemId`, em [`example_item_id.py`](../scafold/src/scafold/domain/bounded_context_example/value_objects/example_item_id.py).

### 2. Declarar a entidade

A entidade é um `@dataclass(eq=False)` que estende `Entity[IdT]` e implementa `get_id`. Ela não estende `AggregateRoot` e não registra eventos: quem registra é a raiz. `Entity` fica em [`entity.py`](../scafold/src/scafold/domain/shared/entities/entity.py).

### 3. A raiz guarda a coleção

O agregado declara a lista de filhas com `field(default_factory=list)`. Veja o campo `items` de `Example`, em [`example.py`](../scafold/src/scafold/domain/bounded_context_example/aggregates/example.py).

### 4. A raiz cria a entidade

O método da raiz valida as regras, gera o id, cria a entidade, adiciona à coleção, registra o evento com o id da entidade e devolve a entidade criada. Veja `Example.add_item`: recusa item num Example arquivado (`InvalidTransition`) e nome repetido (`DuplicateItem`), e só então cria o `ExampleItem`, com a posição seguinte, e registra `ExampleItemAdded`.

### 5. Persistir junto com a raiz

A raiz e as filhas vão para duas tabelas na mesma transação: se uma filha falhar, a raiz é revertida junto. Veja `SqlExampleRepository.add`, em [`sql_example_repository.py`](../scafold/src/scafold/infrastructure/persistence/bounded_context_example/sql_example_repository.py), e `ExampleRowMapper.to_item_rows`.

### 6. Testar

Os cenários da regra "só a raiz cria itens" estão em [`example.feature`](../scafold/tests/features/domain/example.feature).

## Guidances relacionados

- [Agregado raiz](agregado-raiz.md) (v1.0.0): a raiz que contém a coleção e as regras.
- [Evento de domínio](evento-de-dominio.md) (v1.0.0): o evento que a raiz registra ao criar a entidade.
- [Repositório e leitor sobre o querier do sqlc](repositorio-e-leitor-sobre-sqlc.md) (v1.0.0): como a raiz e as filhas são gravadas e reconstruídas.

## Change log

| Versão | Data       | Pessoa           | Motivo                                                                                   |
|--------|------------|------------------|------------------------------------------------------------------------------------------|
| 1.0.0  | 2026-11-18 | Guilherme Giusti | Criação: ensinar a escrever entidades filhas criadas só pela raiz, com o scaffold como referência |

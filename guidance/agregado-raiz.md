---
title: Agregado raiz
version: 1.0.0
---

# Agregado raiz

## Propósito

Depois de ler, você saberá escrever a raiz de um agregado: a classe que guarda as regras de negócio e é o único jeito de mudar suas entidades e valores. O guia cobre o identificador, a fábrica `create`, as operações que mudam o estado, os erros de domínio e o momento de registrar um evento. A referência é `Example`, em [`aggregates/example.py`](../scafold/src/scafold/domain/bounded_context_example/aggregates/example.py).

## Problema que resolve

As armadilhas abaixo estão descritas nas docstrings da referência:

- Um `@dataclass` sem `eq=False` gera igualdade por valor e deixa o agregado unhashable.
- Se o agregado consultar repositório, relógio ou serviço externo por conta própria, ele passa a depender de infraestrutura. Por isso o instante e os dados de fora chegam por parâmetro.
- Se o evento for registrado antes de validar a regra, um evento pode sair para uma mudança que não aconteceu.

## Por que foi criado

Pedido de 2026-11-18: guidances que ensinem a implementar seguindo o projeto de referência `../scafold`, para usar em outros repositórios. A decisão que o sustenta é a ADR-002 (Domain Driven Design nos módulos backend).

## Como implementar

### 1. Identificador do agregado

O identificador é um `NewType` sobre `UUID`, em `value_objects/<agregado>_id.py`. A referência é `ExampleId`, em [`example_id.py`](../scafold/src/scafold/domain/bounded_context_example/value_objects/example_id.py). Um valor do domínio que não é identificador, como a categoria, é um tipo próprio: `Category`, um `StrEnum`, em [`category.py`](../scafold/src/scafold/domain/bounded_context_example/value_objects/category.py).

### 2. Declarar a classe

A raiz é um `@dataclass(eq=False)` que estende `AggregateRoot[IdT]` e implementa `get_id`. O campo `events` não é declarado: `AggregateRoot` cria o conjunto no primeiro evento. Veja a declaração de `Example`, com os campos e o `get_id`. `AggregateRoot`, em [`aggregate_root.py`](../scafold/src/scafold/domain/shared/aggregates/aggregate_root.py), oferece `add_event`, `get_uncommitted_events` e `clear_events`; dentro do agregado, só `add_event` é usado.

### 3. A fábrica `create`

`create` recebe tudo o que vem de fora por parâmetro (o instante, a categoria já classificada), valida a regra, gera o id, monta o agregado e registra o evento de criação. A regra quebrada vira erro de domínio antes de qualquer criação. Veja `Example.create`: o nome perde os espaços das pontas, precisa ter de 1 a `MAX_LABEL_LENGTH` caracteres, e `InvalidLabel` sai antes de o objeto existir. O evento registrado é `ExampleCreated`.

Quando a criação não é um fato relevante, `create` só gera o id e devolve o agregado, sem evento.

### 4. Operações que mudam o estado

Toda operação segue a mesma ordem: validar a regra, mudar o estado e só então registrar o evento. Veja `Example.archive`: o segundo arquivamento levanta `InvalidTransition`, e só o primeiro grava `archived_at` e registra `ExampleArchived`.

### 5. Regras que dependem do estado

O estado derivado vira property, e as operações a usam como regra. Veja `Example.is_archived`, consultada por `archive` e por `add_item`.

### 6. Erros de domínio

Cada erro é uma subclasse de `Exception` no próprio módulo, em `errors/` do contexto. A docstring diz a regra; a mensagem descreve a regra e não repete o dado recebido. Veja [`invalid_transition.py`](../scafold/src/scafold/domain/bounded_context_example/errors/invalid_transition.py). Um erro que o banco decide, como a unicidade do nome, também é de domínio, e quem o levanta é o repositório: veja `LabelTaken`, em [`label_taken.py`](../scafold/src/scafold/domain/bounded_context_example/errors/label_taken.py).

### 7. Reconstruir o que foi gravado

Quem reconstrói o agregado a partir do banco usa o construtor, e não `create`: o que já foi gravado não é validado de novo, não ganha id novo e nasce sem eventos. Veja `ExampleRowMapper.to_aggregate`, em [`example_row_mapper.py`](../scafold/src/scafold/infrastructure/persistence/bounded_context_example/mappers/example_row_mapper.py).

### 8. Testar

As regras do agregado são funções puras e se provam sem fake. Veja [`example.feature`](../scafold/tests/features/domain/example.feature), com a tag `@domain`, e os steps em [`test_example.py`](../scafold/tests/domain/test_example.py).

## Quando não se aplica

Este guidance não define de onde vêm o id e o relógio: a referência usa `uuid4()` no agregado e recebe o instante do use case, que o recebe da montagem.

## Guidances relacionados

- [Pacotes e camadas de um módulo](pacotes-e-camadas-do-modulo.md) (v1.0.0): onde ficam os módulos do agregado, do id e dos erros.
- [Entidade filha de um agregado](entidade-filha.md) (v1.0.0): como a raiz cria e protege as entidades filhas.
- [Evento de domínio](evento-de-dominio.md) (v1.0.0): como escrever as classes passadas para `add_event`.
- [Estado modelado por tipos](estado-modelado-por-tipos.md) (v1.0.0): quando o objeto precisa de um tipo por estado.

## Change log

| Versão | Data       | Pessoa           | Motivo                                                                                   |
|--------|------------|------------------|------------------------------------------------------------------------------------------|
| 1.0.0  | 2026-11-18 | Guilherme Giusti | Criação: ensinar a escrever a raiz de um agregado com o scaffold como referência, para uso em outros repositórios |

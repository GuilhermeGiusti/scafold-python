---
title: Estado modelado por tipos
version: 1.0.0
---

# Estado modelado por tipos

## Propósito

Depois de ler, você saberá representar cada estado de um objeto como um tipo próprio, escrever as transições como métodos que devolvem o estado de destino e escrever funções que só aceitam o estado certo, para que o mypy recuse o uso errado antes de o código rodar. A referência é o ciclo de vida de um pedido em [`bounded_context_order/aggregates/order.py`](../scafold/src/scafold/domain/bounded_context_order/aggregates/order.py).

## Problema que resolve

Com um tipo único e um campo de estado, a transição proibida vira um `if` que só falha em runtime, e o campo que só existe em alguns estados vira opcional, obrigando todo leitor a checar se ele existe. Com um tipo por estado, a transição proibida é ausência de método e o campo só existe onde vale.

## Por que foi criado

Pedido de 2026-11-18: guidances que ensinem a implementar seguindo o projeto de referência `../scafold`, para usar em outros repositórios. A decisão que o sustenta é a ADR-007 (Modelagem de estado por tipos).

## Como implementar

### 1. Um tipo por estado

Cada estado é um `@dataclass(frozen=True, slots=True)` com os campos que existem nele, todos obrigatórios. O que é comum fica numa base privada, que não pode ser instanciada: `_OrderBase`, com `id`, `items`, a regra de pedido não vazio e o `total`. Os estados são `PlacedOrder`, `PaidOrder`, `ShippedOrder`, `DeliveredOrder` e `CancelledOrder`. Só `ShippedOrder` e `DeliveredOrder` têm `tracking_code`, e a regra dele fica no `__post_init__` desses dois, que chama `_OrderBase.__post_init__(self)` antes.

O value object do item também se valida na criação: `OrderItem`, em [`order_item.py`](../scafold/src/scafold/domain/bounded_context_order/value_objects/order_item.py).

### 2. A transição é um método do estado de origem

O método recebe os dados novos e devolve uma nova instância do estado de destino; o original não muda. A transição proibida não ganha método. A tabela das transições está na docstring do módulo. `ShippedOrder` não tem `cancel`: pedido enviado não cancela.

### 3. Funções recebem o estado em que fazem sentido

Anote o parâmetro com o tipo do estado, e não com a união. Uma função que despacha um pedido recebe `PaidOrder`, e o mypy recusa a chamada com um `PlacedOrder`.

### 4. A união e o `match` exaustivo

Onde o código aceita qualquer estado, use a união `Order` e descubra o estado com `match`, terminando em `case _: assert_never(...)`. Um estado novo sem o seu `case` vira erro do mypy. Veja a função `label`. As garantias só valem com o mypy rodando: na referência, `uv run mypy` com `strict`.

### 5. Testar o que vale em runtime

As transições e as recusas de estado inválido estão em [`order_states.feature`](../scafold/tests/features/domain/order_states.feature), com os steps em [`test_order_states.py`](../scafold/tests/domain/test_order_states.py). A transição proibida não tem cenário: quem a recusa é o mypy.

## Quando não se aplica

Os estados são imutáveis e não registram eventos. Um agregado que emite eventos de domínio continua no formato de [Agregado raiz](agregado-raiz.md); se um estado modelado por tipos precisar emitir evento, a transição devolve o par (estado, evento), e quem chamou persiste o estado e despacha o evento.

## Guidances relacionados

- [Agregado raiz](agregado-raiz.md) (v1.0.0): como escrever o agregado que registra eventos.

## Change log

| Versão | Data       | Pessoa           | Motivo                                                                                   |
|--------|------------|------------------|------------------------------------------------------------------------------------------|
| 1.0.0  | 2026-11-18 | Guilherme Giusti | Criação: ensinar a representar estados como tipos com o scaffold como referência         |

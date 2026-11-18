# language: pt
Funcionalidade: Drenagem da outbox

  A Strategy publica e relata; quem decide o destino da mensagem é a drenagem. Cada mensagem roda
  numa transação "outbox_drain" própria.

  Regra: o resultado do envio decide o destino da mensagem

    Contexto:
      Dado uma mensagem pendente do evento "example.created"

    Cenário: mensagem aceita pelo broker é marcada como publicada
      Dado o broker aceitando as publicações
      Quando a drenagem roda um ciclo
      Então a mensagem está "PUBLISHED"
      E o ciclo publicou 1, reagendou 0 e matou 0 mensagens

    Cenário: falha transitória reagenda a mensagem e registra a falha
      Dado o broker falhando de forma transitória
      Quando a drenagem roda um ciclo
      Então a mensagem está "PENDING" com 1 tentativas
      E a falha registrada é "TRANSIENTE"
      E o ciclo publicou 0, reagendou 1 e matou 0 mensagens

    Cenário: a quinta falha transitória mata a mensagem
      Dado a mensagem com 4 tentativas
      E o broker falhando de forma transitória
      Quando a drenagem roda um ciclo
      Então a mensagem está "DEAD"
      E a métrica de mortas registrou o motivo "attempts_exhausted"

    Cenário: falha permanente mata a mensagem na hora
      Dado o broker falhando de forma permanente
      Quando a drenagem roda um ciclo
      Então a mensagem está "DEAD"
      E a falha registrada é "PERMANENTE"
      E a métrica de mortas registrou o motivo "permanent"

  Regra: fila vazia é estado normal

    Cenário: o ciclo sem trabalho commita vazio e publica o backlog zerado
      Quando a drenagem roda um ciclo
      Então o ciclo publicou 0, reagendou 0 e matou 0 mensagens
      E o backlog publicado é zero para "rabbitmq"
      E a transação "outbox_drain" commitou

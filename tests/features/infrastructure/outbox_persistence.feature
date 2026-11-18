# language: pt
@integration
Funcionalidade: Outbox sobre o Postgres

  O que só o banco real prova: o evento e o estado existem juntos ou não existem, e a drenagem
  reivindica a linha gravada.

  Regra: o evento é gravado na transação que grava o estado

    Cenário: o evento gravado na transação que commita fica pendente, carimbado e com o id do trace
      Quando gravo o Example "Relatório" e o evento de integração na mesma transação
      Então a tabela "outbox_message" tem 1 linhas com o status "PENDING"
      E a mensagem gravada foi carimbada "rabbitmq" com o id do trace da gravação

    Cenário: o rollback não deixa nem o estado nem a mensagem
      Quando gravo o Example "Relatório" e o evento na mesma transação, e ela falha antes do commit
      Então a tabela "example" tem 0 linhas
      E a tabela "outbox_message" tem 0 linhas
      E a tabela "outbox_message_rabbitmq" tem 0 linhas

    Cenário: gravar o evento fora de uma transação é recusado
      Quando gravo o evento de integração fora de uma transação
      Então a operação é recusada por escrita fora da transação

  Regra: a drenagem reivindica a linha gravada e aplica o resultado

    Cenário: a mensagem gravada é publicada pela drenagem
      Dado o Example "Relatório" e o evento de integração gravados
      Quando a drenagem sobre o banco roda um ciclo com o broker aceitando
      Então a tabela "outbox_message" tem 1 linhas com o status "PUBLISHED"

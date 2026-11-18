# language: pt
Funcionalidade: Criar Example

  O use case decide a ordem: classifica, monta e valida fora da transação; grava o Example e o
  evento de integração dentro dela; despacha os eventos de domínio depois do commit.

  Regra: a criação grava tudo numa transação só

    Cenário: Example criado é gravado com os itens, na transação "create_example"
      Quando crio o Example "Relatório premium" com os itens "Capa, Sumário"
      Então o Example gravado tem o nome "Relatório premium", a categoria "premium" e 2 itens
      E a única transação aberta foi "create_example", e ela commitou

    Cenário: a criação grava o evento de integração junto com o Example
      Quando crio o Example "Relatório" com os itens "Capa"
      Então a outbox guarda o evento "example.created" para o destino "example"

    Cenário: os eventos de domínio são despachados depois do commit
      Quando crio o Example "Relatório" com os itens "Capa"
      Então foram despachados os eventos "created, item_added"

  Regra: a recusa não grava nada e não despacha nada

    Cenário: nome já usado é recusado, e nada da segunda criação fica gravado
      Dado um Example "Relatório" já gravado
      Quando crio o Example "Relatório" com os itens "Capa"
      Então a operação é recusada por nome já usado
      E a outbox guarda 1 evento de integração
      E foram despachados os eventos "created"

    Cenário: item repetido é recusado antes de abrir a transação
      Quando crio o Example "Relatório" com os itens "Capa, Capa"
      Então a operação é recusada por item repetido
      E nenhuma transação foi aberta

    Cenário: nome em branco é recusado pelo domínio, antes de abrir a transação
      Quando crio o Example "   " com os itens "Capa"
      Então a operação é recusada por nome inválido
      E nenhuma transação foi aberta

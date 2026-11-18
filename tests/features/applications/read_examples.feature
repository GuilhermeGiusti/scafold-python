# language: pt
Funcionalidade: Ler e limpar Examples

  Regra: a consulta devolve uma cópia sem comportamento, e não o agregado

    Cenário: a consulta devolve o Example com os itens, na ordem
      Dado um Example "Relatório" já gravado com os itens "Capa, Sumário"
      Quando consulto esse Example
      Então a consulta devolve o nome "Relatório" e os itens "Capa, Sumário"

    Cenário: consultar um Example inexistente é recusado
      Quando consulto o Example "0b6f3c52-9d0f-4d0e-8a43-5b8f6f1a2c11"
      Então a operação é recusada por example inexistente

  Regra: a listagem devolve resumos por nome, até o limite

    Cenário: a listagem respeita a ordem por nome e o limite
      Dado um Example "B" já gravado com os itens "Capa"
      E um Example "A" já gravado com os itens "Capa, Sumário"
      E um Example "C" já gravado
      Quando listo até 2 Examples
      Então a listagem devolve os nomes "A, B"

  Regra: a limpeza remove só os arquivados

    Cenário: os arquivados saem e os ativos ficam
      Dado um Example "A" já gravado e arquivado
      E um Example "B" já gravado
      Quando removo os Examples arquivados
      Então a listagem completa tem os nomes "B"
      E a última transação aberta foi "purge_archived_examples"

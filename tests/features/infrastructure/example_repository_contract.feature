# language: pt
@contract
Funcionalidade: Contrato do repositório e do leitor de Example

  O mesmo cenário roda contra o fake em memória e contra o adaptador SQL sobre o Postgres. O fake
  só é confiável porque passa por aqui. Nenhum passo diz qual implementação está por trás.

  Regra: o que foi gravado numa transação é lido de volta

    Cenário: o Example gravado volta com os itens, na ordem
      Dado um Example "Relatório" com os itens "Capa, Sumário" gravado numa transação
      Quando leio esse Example
      Então ele volta com o nome "Relatório", a categoria "standard" e os itens "Capa, Sumário"

    Cenário: ler um Example que não existe não devolve nada
      Quando leio um Example que não existe
      Então nada volta

    Cenário: arquivar grava o instante, e a limpeza remove só os arquivados
      Dado um Example "A" com os itens "Capa" gravado numa transação
      E um Example "B" com os itens "Capa" gravado numa transação
      Quando arquivo "A" e removo os arquivados, numa transação
      Então a limpeza removeu 1 Example
      E a listagem tem os nomes "B"

  Regra: o nome é único

    Cenário: nome repetido é recusado, e o primeiro fica
      Dado um Example "Relatório" com os itens "Capa" gravado numa transação
      Quando gravo outro Example "Relatório" numa transação
      Então a operação é recusada por nome já usado
      E a listagem tem os nomes "Relatório"

  Regra: escrever exige a transação, e o erro dentro dela desfaz tudo

    Cenário: gravar fora de uma transação é recusado
      Quando gravo um Example "Relatório" fora de uma transação
      Então a operação é recusada por escrita fora da transação

    Cenário: o erro dentro da transação desfaz a gravação
      Quando gravo um Example "Relatório" numa transação que falha depois
      Então a listagem está vazia

# language: pt
@domain
Funcionalidade: Agregado Example

  O agregado é o único jeito de mudar o Example e os seus itens. Toda operação valida a regra,
  muda o estado e só então registra o fato.

  Regra: a criação valida o nome e registra o fato

    Cenário: Example criado perde os espaços das pontas do nome e registra a criação
      Quando crio um Example com o nome "  Relatório  " na categoria "premium"
      Então o Example tem o nome "Relatório" e a categoria "premium"
      E o Example criado registrou os eventos "created"

    Cenário: nome só com espaços é recusado
      Quando crio um Example com um nome só de espaços
      Então a operação é recusada por nome inválido

    Esquema do Cenário: nome de 1 a 64 caracteres é aceito
      Quando crio um Example com um nome de <tamanho> caracteres
      Então o Example é criado

      Exemplos:
        | tamanho |
        | 1       |
        | 64      |

    Cenário: nome de 65 caracteres é recusado
      Quando crio um Example com um nome de 65 caracteres
      Então a operação é recusada por nome inválido

  Regra: só a raiz cria itens, com nome único, e nunca num Example arquivado

    Cenário: item novo entra no fim da lista e registra o fato
      Dado um Example "Relatório" com o item "Capa"
      Quando adiciono o item "Sumário"
      Então o Example tem os itens "Capa, Sumário", nesta ordem
      E o Example registrou os eventos "created, item_added, item_added"

    Cenário: item com nome repetido é recusado e nada muda
      Dado um Example "Relatório" com o item "Capa"
      Quando adiciono o item "Capa"
      Então a operação é recusada por item repetido
      E o Example tem os itens "Capa", nesta ordem

    Cenário: Example arquivado não recebe itens
      Dado um Example "Relatório" arquivado
      Quando adiciono o item "Capa"
      Então a operação é recusada por transição inválida

  Regra: arquivar acontece uma vez só

    Cenário: o primeiro arquivamento grava o instante e registra o fato
      Dado um Example "Relatório" com o item "Capa"
      Quando arquivo o Example em "2026-11-19T08:30:00+00:00"
      Então o Example está arquivado desde "2026-11-19T08:30:00+00:00"
      E o Example registrou os eventos "created, item_added, archived"

    Cenário: o segundo arquivamento é recusado
      Dado um Example "Relatório" arquivado
      Quando arquivo o Example em "2026-11-20T08:30:00+00:00"
      Então a operação é recusada por transição inválida

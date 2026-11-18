# language: pt
Funcionalidade: Mappers nas periferias do domínio

  Regra: o mapper de persistência guarda o detalhe de armazenamento e volta ao mesmo agregado

    Cenário: o agregado vai ao formato gravado e volta igual
      Dado um Example "Relatório" da categoria "premium" com os itens "Capa, Sumário"
      Quando o Example vai ao formato gravado e volta
      Então o Example reconstruído é igual ao original
      E o Example reconstruído nasce sem eventos

    Esquema do Cenário: a categoria é gravada como um código de uma letra
      Dado um Example "Relatório" da categoria "<categoria>" com os itens "Capa"
      Quando o Example vai ao formato gravado
      Então o código gravado da categoria é "<código>"

      Exemplos:
        | categoria | código |
        | standard  | S      |
        | premium   | P      |

  Regra: o vocabulário do fornecedor morre no mapper anti-corrupção

    Esquema do Cenário: o termo do fornecedor vira a categoria do domínio
      Quando o fornecedor classifica "<nome>"
      Então a categoria devolvida é "<categoria>"

      Exemplos:
        | nome              | categoria |
        | Relatório premium | premium   |
        | Relatório         | standard  |

    Cenário: um termo desconhecido falha na fronteira e é contado com o nome do adaptador
      Dado o fornecedor respondendo com o tier "DIAMOND"
      Quando o fornecedor classifica "Relatório"
      Então a operação é recusada por payload sem tradução
      E o erro de tradução foi contado para o adaptador "category_gateway"

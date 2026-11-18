# language: pt
Funcionalidade: Arquivar Example

  Regra: arquivar grava o instante uma vez só e despacha o fato depois do commit

    Cenário: Example arquivado grava o instante do relógio
      Dado um Example "Relatório" já gravado
      Quando arquivo esse Example
      Então o Example gravado está arquivado desde "2026-11-18T12:00:00+00:00"
      E foram despachados os eventos "created, archived"

    Cenário: arquivar duas vezes é recusado
      Dado um Example "Relatório" já gravado e arquivado
      Quando arquivo esse Example
      Então a operação é recusada por transição inválida

  Regra: o que não existe é resposta ao pedido, e não regra do domínio

    Cenário: Example inexistente é recusado
      Quando arquivo o Example "0b6f3c52-9d0f-4d0e-8a43-5b8f6f1a2c11"
      Então a operação é recusada por example inexistente

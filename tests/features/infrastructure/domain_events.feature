# language: pt
Funcionalidade: Despacho de eventos de domínio no processo

  Regra: o evento chega a quem o escuta, depois do commit

    Cenário: o handler do evento e o handler de todos os eventos recebem o despacho
      Dado os handlers do processo registrados
      Quando o Example "Relatório" criado é despachado
      Então o handler da criação avisou "categoria standard"
      E o handler de todos os eventos registrou "bounded_context_example.example.created"
      E a publicação de "bounded_context_example.example.created" foi contada

  Regra: a falha de um handler não interrompe os seguintes

    Cenário: o handler que falha é medido como erro, e o próximo roda
      Dado um handler que falha registrado antes dos handlers do processo
      Quando o Example "Relatório" criado é despachado
      Então o tratamento de "FailingHandler" foi medido como "error"
      E o tratamento de "ExampleCreatedHandler" foi medido como "ok"
      E o handler da criação avisou "categoria standard"

# language: pt
Funcionalidade: Observação padrão de todo use case

  Nenhum use case chega cru à borda: o decorator mede, abre o span "use_case <nome>", registra no
  log e relança a exceção.

  Regra: a execução é medida com o nome literal do use case

    Cenário: a execução que termina bem é medida como ok e abre o span do use case
      Quando a borda cria o Example "Relatório"
      Então a execução de "create_example" foi medida como "ok" com o erro "none"
      E o span "use_case create_example" foi aberto com o status "ok"
      E o span "db.transaction create_example" não existe, porque a Unit of Work é o fake

  Regra: a falha é medida com a classe do erro, relançada, e nunca leva a mensagem

    Cenário: a recusa é medida como erro, e o span sai marcado com a classe do erro
      Quando a borda cria o Example "   "
      Então a operação é recusada por nome inválido
      E a execução de "create_example" foi medida como "error" com o erro "InvalidLabel"
      E o span "use_case create_example" saiu como erro com a descrição "InvalidLabel"
      E o span "use_case create_example" não tem eventos de exceção

  Regra: os decorators síncronos seguem a mesma regra dos assíncronos

    Cenário: o use case síncrono é medido e abre o span com o nome literal
      Quando a borda executa um use case síncrono rotulado "count_items"
      Então o decorator síncrono mediu "count_items" como "ok"
      E o span "use_case count_items" foi aberto com o status "ok"

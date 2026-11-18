# language: pt
Funcionalidade: Nível do log pela variável LOG_DEBUG

  Por padrão o log mostra só o que pede atenção: aviso e erro. Com LOG_DEBUG=true, mostra tudo,
  inclusive os registros de rotina (início e fim de use case, medições escritas no log). O nível é
  aplicado no logger raiz, então vale também para as bibliotecas de terceiros.

  Regra: sem LOG_DEBUG, só aviso e erro aparecem

    Cenário: os registros de rotina ficam fora do log
      Dado o log configurado com LOG_DEBUG igual a "false"
      Quando o processo registra uma linha em cada nível
      Então aparecem no log exatamente os níveis "WARNING, ERROR"

    Cenário: a regra vale também para um logger de terceiros
      Dado o log configurado com LOG_DEBUG igual a "false"
      Quando uma biblioteca de terceiros registra uma linha em cada nível
      Então aparecem no log exatamente os níveis "WARNING, ERROR"

  Regra: com LOG_DEBUG=true, tudo aparece

    Cenário: todos os níveis aparecem
      Dado o log configurado com LOG_DEBUG igual a "true"
      Quando o processo registra uma linha em cada nível
      Então aparecem no log exatamente os níveis "DEBUG, INFO, WARNING, ERROR"

  Regra: toda linha é um JSON com campos fixos, e a mensagem da exceção nunca é escrita

    Cenário: a exceção sai com a classe e a pilha de chamadas, sem a mensagem
      Dado o log configurado com LOG_DEBUG igual a "false"
      Quando o processo registra uma exceção com a mensagem "pessoa@exemplo.com"
      Então a linha do erro tem os campos fixos, o tipo de erro "RuntimeError" e a pilha
      E "pessoa@exemplo.com" não aparece no log

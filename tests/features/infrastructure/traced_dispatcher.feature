# language: pt
Funcionalidade: Span de envio da outbox

  O envoltório abre o span "outbox.dispatch <evento>" por fora da Strategy e da drenagem, e
  continua o trace de quem gravou o evento (emenda da ADR-006).

  Contexto:
    Dado uma mensagem gravada dentro do trace "4bf92f3577b34da6a3ce929d0e0e4736"

  Regra: o envio aparece no trace do produtor, com os atributos do contrato

    Cenário: o span de envio continua o trace gravado na linha
      Dado a Strategy aceitando a publicação
      Quando o envoltório envia a mensagem
      Então o span "outbox.dispatch example.created" pertence ao trace "4bf92f3577b34da6a3ce929d0e0e4736"
      E o span de envio tem exatamente os atributos do contrato

  Regra: a falha leva só o tipo do resultado, nunca o detalhe

    Cenário: a falha permanente marca o span sem a mensagem do broker
      Dado a Strategy falhando de forma permanente com o detalhe "exchange inexistente"
      Quando o envoltório envia a mensagem
      Então o span de envio saiu como erro com a descrição "permanent_error"
      E "exchange inexistente" não aparece no span de envio

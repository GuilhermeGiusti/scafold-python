# language: pt
@integration
Funcionalidade: Strategy de publicação no RabbitMQ

  A Strategy publica e relata, sem lançar. Ela não cria a exchange: destino inexistente é falha
  permanente, e não uma exchange criada por acidente.

  Regra: o resultado do envio é relatado como um dos três casos

    Cenário: a mensagem publicada numa exchange ligada a uma fila é aceita
      Dado o RabbitMQ com a exchange "example" ligada a uma fila
      Quando a Strategy publica uma mensagem para o destino "example"
      Então o resultado é "publicada"
      E a fila recebeu a mensagem com o cabeçalho "message_id"

    Cenário: destino sem exchange é falha permanente
      Quando a Strategy publica uma mensagem para o destino "inexistente"
      Então o resultado é "falha permanente"

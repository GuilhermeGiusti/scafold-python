# language: pt
Funcionalidade: Comando de shell

  A linha de comando chama os mesmos use cases da API. O resultado sai em JSON na saída padrão, e
  o código de saída diz o que aconteceu.

  Regra: o comando executa o use case e escreve o resultado em JSON

    Cenário: criar escreve o id na saída padrão e termina com o código 0
      Quando executo o comando "create-example --label Relatório --item Capa --item Sumário"
      Então o comando termina com o código 0
      E a saída padrão tem o JSON com o campo "id"

    Cenário: listar escreve os resumos por nome
      Dado o comando "create-example --label B" executado
      E o comando "create-example --label A --item Capa" executado
      Quando executo o comando "list-examples --limit 10"
      Então o comando termina com o código 0
      E a saída padrão lista os nomes "A, B"

  Regra: a recusa sai com o código 3 e o erro em JSON na saída de erro

    Cenário: nome repetido é recusado
      Dado o comando "create-example --label Relatório" executado
      Quando executo o comando "create-example --label Relatório"
      Então o comando termina com o código 3
      E a saída de erro tem o código "label_taken"

  Regra: argumento e configuração são conferidos antes de tocar o banco

    Esquema do Cenário: argumento inválido é recusado pelo parser com o código 2
      Quando executo o processo com o comando "<comando>" e sem configuração
      Então o comando termina com o código 2

      Exemplos:
        | comando                          |
        | archive-example --id nao-e-uuid  |
        | list-examples --limit 0          |
        | comando-que-nao-existe           |

    Cenário: sem configuração o processo recusa com o código 1 e cita a variável
      Quando executo o processo com o comando "list-examples" e sem configuração
      Então o comando termina com o código 1
      E a saída de erro cita a variável "OTEL_SERVICE_NAME"

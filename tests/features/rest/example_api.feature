# language: pt
Funcionalidade: API de Example

  Um cenário por status documentado de cada rota, e uma linha por entrada inválida.

  Regra: criar devolve o id, e o Example criado pode ser consultado

    Cenário: criar responde 201 com o id gerado
      Quando crio pela API o Example "Relatório premium" com os itens "Capa, Sumário"
      Então a resposta tem o status 201
      E a consulta pela API do id devolvido traz o nome "Relatório premium", a categoria "premium" e 2 itens

    Cenário: nome repetido responde 409
      Dado o Example "Relatório" criado pela API
      Quando crio pela API o Example "Relatório" com os itens "Capa"
      Então a resposta tem o status 409
      E o erro tem o código "label_taken"

    Cenário: itens com nome repetido respondem 409
      Quando crio pela API o Example "Relatório" com os itens "Capa, Capa"
      Então a resposta tem o status 409
      E o erro tem o código "duplicate_item"

    Cenário: nome só com espaços responde 400
      Quando crio pela API o Example "   " com os itens "Capa"
      Então a resposta tem o status 400
      E o erro tem o código "invalid_label"

  Regra: consultar, listar e arquivar respondem pelo estado do Example

    Cenário: consultar um id que não existe responde 404
      Quando acesso "GET /api/v1/examples/0b6f3c52-9d0f-4d0e-8a43-5b8f6f1a2c11"
      Então a resposta tem o status 404
      E o erro tem o código "example_not_found"

    Cenário: listar responde 200 com os resumos por nome
      Dado o Example "B" criado pela API
      E o Example "A" criado pela API
      Quando acesso "GET /api/v1/examples?limit=10"
      Então a resposta tem o status 200
      E a listagem traz os nomes "A, B"

    Cenário: arquivar responde 204, e arquivar de novo responde 409
      Dado o Example "Relatório" criado pela API
      Quando arquivo pela API o Example criado duas vezes
      Então a resposta tem o status 409
      E o erro tem o código "invalid_transition"

  Regra: toda entrada é validada na borda, e a recusa aponta o campo

    Esquema do Cenário: corpo inválido responde 422 apontando o campo
      Quando envio para "POST /api/v1/examples" o corpo <corpo>
      Então a resposta tem o status 422
      E o erro tem o código "invalid_request"
      E o campo recusado é "<campo>"

      Exemplos:
        | corpo                                       | campo            |
        | {"displayName": 3}                          | body.displayName |
        | {"displayName": "A", "extra": true}         | body.extra       |
        | {"itemNames": ["Capa"]}                     | body.displayName |
        | {"displayName": "A", "itemNames": [""]}     | body.itemNames.0 |
        | {"displayName": ""}                         | body.displayName |

    Esquema do Cenário: parâmetro inválido responde 422 apontando o parâmetro
      Quando acesso "<rota>"
      Então a resposta tem o status 422
      E o campo recusado é "<campo>"

      Exemplos:
        | rota                                    | campo              |
        | GET /api/v1/examples?limit=0            | query.limit        |
        | GET /api/v1/examples?limit=101          | query.limit        |
        | GET /api/v1/examples/nao-e-uuid         | path.example_id    |

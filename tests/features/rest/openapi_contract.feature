# language: pt
Funcionalidade: Contrato OpenAPI

  Regra: toda rota da aplicação documenta entrada, saída e status, e valida a entrada

    Esquema do Cenário: nenhuma rota da aplicação descumpre a regra
      Quando procuro <violação>
      Então nada é encontrado

      Exemplos:
        | violação                                                        |
        | rotas sem resumo ou sem descrição                               |
        | rotas sem o modelo da resposta de sucesso                       |
        | rotas sem os erros de validação e de defeito                    |
        | rotas com erro sem descrição ou fora do formato de erro         |
        | rotas com campo de entrada sem descrição, exemplo ou restrição  |
        | rotas com campo de saída sem descrição ou exemplo               |
        | rotas com corpo que aceita campo desconhecido                   |
        | rotas com corpo que converte texto em número                    |

  Regra: uma rota escrita sem documentação é acusada por todas as regras

    Esquema do Cenário: a rota sem documentação é acusada
      Dado uma aplicação com rotas escritas sem documentação
      Quando procuro <violação>
      Então a rota "<rota>" é encontrada

      Exemplos:
        | violação                                                        | rota        |
        | rotas sem resumo ou sem descrição                               | POST /loose |
        | rotas sem o modelo da resposta de sucesso                       | GET /loose  |
        | rotas sem os erros de validação e de defeito                    | POST /loose |
        | rotas com erro sem descrição ou fora do formato de erro         | POST /loose |
        | rotas com campo de entrada sem descrição, exemplo ou restrição  | POST /loose |
        | rotas com campo de saída sem descrição ou exemplo               | POST /loose |
        | rotas com corpo que aceita campo desconhecido                   | POST /loose |
        | rotas com corpo que converte texto em número                    | POST /loose |

  Regra: o 422 é exigido só em rota com entrada, e o 500 em toda rota

    Cenário: a rota com entrada que não documenta o 422 é acusada
      Dado uma aplicação com rotas escritas sem documentação
      Quando procuro rotas sem os erros de validação e de defeito
      Então a rota "GET /loose/limited" é encontrada

    Cenário: a rota sem entrada que documenta só o 500 não é acusada
      Dado uma aplicação com rotas escritas sem documentação
      Quando procuro rotas sem os erros de validação e de defeito
      Então a rota "GET /loose/status" não é encontrada

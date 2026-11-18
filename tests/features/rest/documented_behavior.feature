# language: pt
@fuzz
Funcionalidade: A API só devolve o que documenta

  Esquema do Cenário: nenhuma resposta foge do contrato
    Quando exercito cada rota com requisições <tipo> geradas a partir do documento OpenAPI
    Então nenhuma resposta foge do contrato

    Exemplos:
      | tipo      |
      | válidas   |
      | inválidas |

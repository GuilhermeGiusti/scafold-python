# language: pt
Funcionalidade: Health check da API

  Regra: o processo de pé responde 200, sem consultar dependências

    Cenário: o health check responde 200 com o status ok
      Quando acesso "GET /api/v1/health/check"
      Então a resposta tem o status 200
      E o corpo da resposta tem o status "ok"

  Regra: o health check nasce documentado, como toda rota

    Cenário: a rota está no documento OpenAPI com resumo e o 500 documentado
      Quando procuro a rota "GET /api/v1/health/check" no documento OpenAPI da aplicação
      Então a rota está documentada
      E a rota documenta os status "200, 500"

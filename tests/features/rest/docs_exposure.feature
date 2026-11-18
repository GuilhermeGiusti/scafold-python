# language: pt
Funcionalidade: Exposição do Swagger

  Toda rota nasce documentada no código; a variável API_EXPOSE_DOCS só decide se a tela e o
  documento são servidos. Desligada por padrão: produção não precisa lembrar de desligar.

  Esquema do Cenário: o Swagger só é servido quando a configuração liga
    Dado o processo configurado com <configuração>
    Quando acesso "GET <caminho>"
    Então a resposta tem o status <status>

    Exemplos:
      | configuração                    | caminho       | status |
      | API_EXPOSE_DOCS igual a "true"  | /docs         | 200    |
      | API_EXPOSE_DOCS igual a "true"  | /openapi.json | 200    |
      | API_EXPOSE_DOCS igual a "false" | /docs         | 404    |
      | nenhuma variável                | /docs         | 404    |
      | nenhuma variável                | /openapi.json | 404    |

  Cenário: o documento existe mesmo com o Swagger desligado
    Dado o processo configurado com nenhuma variável
    Quando procuro a rota "POST /api/v1/examples" no documento OpenAPI da aplicação
    Então a rota está documentada

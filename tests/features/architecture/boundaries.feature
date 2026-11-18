# language: pt
Funcionalidade: Fronteiras entre as camadas

  As regras de camada não dependem de review: os imports são lidos pela árvore sintática, e um
  texto que cita um módulo numa string ou num comentário não conta.

  Regra: o lado de dentro não importa borda, adaptador, schema nem framework

    Esquema do Cenário: a camada não importa o que fica fora dela
      Quando procuro os imports da camada "<camada>"
      Então nenhum começa com "<proibidos>"

      Exemplos:
        | camada       | proibidos                                                                                                        |
        | domain       | scafold.applications, scafold.infrastructure, scafold.bootstrap, fastapi, pydantic, sqlalchemy, opentelemetry, blinker, streamlit, aio_pika |
        | applications | scafold.infrastructure, scafold.bootstrap, fastapi, pydantic, sqlalchemy, opentelemetry, blinker, streamlit, aio_pika                      |

    Cenário: a regra acusa um import proibido
      Quando procuro os imports do código "from scafold.infrastructure.rest.example_schemas import X"
      Então "scafold.infrastructure.rest.example_schemas" é encontrado

  Regra: só o ponto de entrada lê o ambiente

    Cenário: nenhum módulo de src lê variável de ambiente
      Quando procuro quem lê o ambiente em "src"
      Então ninguém é encontrado

    Cenário: a regra acusa quem lê o ambiente
      Quando procuro quem lê o ambiente no código "import os\nvalue = os.environ.get('X')"
      Então alguém é encontrado

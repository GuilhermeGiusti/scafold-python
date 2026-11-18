# language: pt
Funcionalidade: Configuração lida do ambiente

  Contexto:
    Dado o ambiente com o nome do serviço, a URL do banco e o carimbo da outbox

  Regra: LOG_DEBUG nasce desligada, e o log mostra só aviso e erro

    Cenário: sem LOG_DEBUG, o nível do log é WARNING
      Quando a configuração é lida
      Então o nível do log é "WARNING"

    Esquema do Cenário: LOG_DEBUG liga e desliga o log de tudo
      Dado a variável "LOG_DEBUG" igual a "<valor>"
      Quando a configuração é lida
      Então o nível do log é "<nível>"

      Exemplos:
        | valor | nível   |
        | true  | DEBUG   |
        | false | WARNING |

  Regra: os interruptores só aceitam true e false, e a recusa não repete o valor

    Esquema do Cenário: valor fora de true e false é recusado
      Dado a variável "<variável>" igual a "<valor>"
      Quando a configuração é lida
      Então a operação é recusada por configuração inválida
      E a recusa cita a variável "<variável>" sem repetir "<valor>"

      Exemplos:
        | variável                  | valor |
        | LOG_DEBUG                 | 1     |
        | LOG_DEBUG                 | True  |
        | API_EXPOSE_DOCS           | yes   |
        | TELEMETRY_METRICS_ENABLED | 0     |

  Regra: cada sinal de telemetria tem a sua variável, e os dois nascem ligados

    Cenário: sem as variáveis de telemetria, os dois sinais ficam ligados e o Swagger desligado
      Quando a configuração é lida
      Então o envio de métricas e o de traces ficam ligados
      E o Swagger fica desligado

  Regra: o que identifica o processo é obrigatório e tem formato

    Esquema do Cenário: sem a variável, a configuração é recusada
      Dado o ambiente sem a variável "<variável>"
      Quando a configuração é lida
      Então a operação é recusada por configuração inválida
      E a recusa cita a variável "<variável>" sem repetir "segredo"

      Exemplos:
        | variável          |
        | OTEL_SERVICE_NAME |
        | DATABASE_URL      |
        | OUTBOX_DISPATCHER |

    Esquema do Cenário: valor fora do formato é recusado sem repetir o valor
      Dado a variável "<variável>" igual a "<valor>"
      Quando a configuração é lida
      Então a operação é recusada por configuração inválida
      E a recusa cita a variável "<variável>" sem repetir "<valor>"

      Exemplos:
        | variável          | valor                                    |
        | DATABASE_URL      | postgresql+asyncpg://app:segredo@db/app  |
        | OUTBOX_DISPATCHER | sns                                      |

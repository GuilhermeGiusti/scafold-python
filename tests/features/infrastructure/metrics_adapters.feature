# language: pt
Funcionalidade: Adaptadores de métricas escolhidos pela montagem

  Cada porta de métricas tem dois adaptadores. Com as métricas ligadas, a montagem entrega os
  OpenTelemetry; desligadas, os de log, que escrevem a medição em DEBUG.

  Regra: com as métricas ligadas, cada porta publica o instrumento do catálogo

    Esquema do Cenário: a medição chega ao leitor de métricas com o nome do catálogo
      Dado as métricas do processo ligadas
      Quando <medição>
      Então o leitor de métricas recebe o instrumento "<instrumento>"

      Exemplos:
        | medição                                | instrumento                 |
        | um use case termina                    | use_case.executions         |
        | uma transação termina                  | db.transactions             |
        | um evento de domínio é publicado       | domain.events.published     |
        | um erro de tradução é contado          | external.translation.errors |
        | uma tentativa de entrega é registrada  | outbox.dispatched           |

  Regra: com as métricas desligadas, a medição vai para o log, e não some

    Cenário: o use case medido aparece no log em DEBUG, no formato do Prometheus
      Dado as métricas do processo desligadas
      Quando um use case termina
      Então o log recebe em DEBUG "use_case_executions_total{use_case=create_example,status=ok,error_type=none} +1"

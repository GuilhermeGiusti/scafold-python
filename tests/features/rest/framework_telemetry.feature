# language: pt
Funcionalidade: Telemetria do framework HTTP

  O FastAPI mede e rastreia por conta própria: sem o argumento `telemetry`, ele usaria os providers
  globais e enviaria ao encontrar as variáveis OTEL_EXPORTER_OTLP_* no ambiente.

  Cenário: nenhum app é criado sem dizer o que fazer com a telemetria do framework
    Quando procuro no código do projeto onde um app é criado
    Então todo app encontrado declara a telemetria do framework

  Cenário: com as métricas desligadas, o framework recebe os providers da montagem e não lê o ambiente
    Quando leio a configuração que a montagem entrega ao framework com as métricas desligadas
    Então o framework recebe o provider de traces da montagem
    E as métricas, os logs e a leitura do ambiente do framework estão desligados

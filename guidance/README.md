# Guidances

Guidances ensinam **como implementar** cada abordagem do software. Cada um aponta o arquivo e o símbolo do projeto de referência [`../scafold`](../scafold/README.md), que é a única fonte do código: os guidances não trazem trechos de código, para não divergirem dele.

Um guidance responde "como eu escrevo isso?". O que decide a arquitetura (quais camadas existem, qual tecnologia adotar) é das ADRs, citadas em cada guidance pelo número e pelo título. Os arquivos das ADRs não acompanham este conjunto.

## Como usar em outro repositório

1. Copie esta pasta e a pasta `scafold` lado a lado: os links usam o caminho relativo `../scafold/...`.
2. Comece por [Pacotes e camadas de um módulo](pacotes-e-camadas-do-modulo.md) e [Montagem do processo e pontos de entrada](montagem-e-pontos-de-entrada.md).
3. Ao escrever uma peça nova, abra o guidance dela, siga os passos e confira o arquivo de referência apontado em cada passo.
4. Toda mudança num guidance aumenta a versão e ganha uma linha no change log. O `(vX.Y.Z)` depois de um link é a versão consultada, e só precisa mudar quando o guidance apontado muda o que se implementa (MINOR ou MAJOR).

## Índice

| Assunto | Guidance | O que ensina |
|---|---|---|
| Estrutura | [Pacotes e camadas de um módulo](pacotes-e-camadas-do-modulo.md) (v1.0.0) | onde fica cada peça, nomes e imports |
| Estrutura | [Montagem do processo e pontos de entrada](montagem-e-pontos-de-entrada.md) (v1.0.0) | a fundação, a montagem de cada borda e a ordem do boot |
| Estrutura | [Configuração pelo ambiente e nível do log](configuracao-pelo-ambiente.md) (v1.0.0) | `Settings`, interruptores estritos, recusa sem repetir o valor, `LOG_DEBUG` |
| Domínio | [Agregado raiz](agregado-raiz.md) (v1.0.0) | a raiz com as regras, a fábrica `create` e os erros de domínio |
| Domínio | [Entidade filha de um agregado](entidade-filha.md) (v1.0.0) | a entidade criada só pela raiz |
| Domínio | [Evento de domínio](evento-de-dominio.md) (v1.0.0) | a classe do evento e o `add_event` |
| Domínio | [Handler de evento de domínio](handler-de-evento-de-dominio.md) (v1.0.0) | o handler, o registro no manager e a falha isolada |
| Domínio | [Estado modelado por tipos](estado-modelado-por-tipos.md) (v1.0.0) | um tipo por estado, conferido pelo mypy |
| Aplicação | [Commands, queries e use cases](commands-queries-e-use-cases.md) (v1.0.0) | os oito contratos, o DTO de saída e o decorator obrigatório |
| Dados | [Unit of Work com métricas](unit-of-work-com-metricas.md) (v1.0.0) | a transação nomeada, medida e rastreada |
| Dados | [Repositório e leitor sobre o querier do sqlc](repositorio-e-leitor-sobre-sqlc.md) (v1.0.0) | a porta, o adaptador SQL, o mapper de persistência e o leitor dedicado |
| Dados | [Migrations e queries SQL](migrations-e-queries-sql.md) (v1.0.0) | o SQL-fonte, o Flyway e as restrições nomeadas |
| Dados | [Geração de código com sqlc](geracao-de-codigo-com-sqlc.md) (v1.0.0) | o `sqlc.yaml`, `make generate` e os portões |
| Bordas | [Mappers e presenters](mappers-e-presenters.md) (v1.0.0) | as traduções em cada fronteira, com o mapper anti-corrupção |
| Bordas | [API REST documentada e validada](api-rest-documentada-e-validada.md) (v1.0.0) | rotas com Swagger completo, entrada validada e o health check |
| Bordas | [Comando de linha de comando](linha-de-comando.md) (v1.0.0) | o use case exposto como comando de shell |
| Bordas | [Tela Streamlit](tela-streamlit.md) (v1.0.0) | a página sobre os use cases e o event loop de fundo |
| Integração | [Evento de integração pela outbox](evento-de-integracao-pela-outbox.md) (v1.0.0) | o gravador, a Strategy, o span de envio e o job |
| Observabilidade | [Telemetria com OpenTelemetry](telemetria-com-opentelemetry.md) (v1.0.0) | providers, adaptadores de métricas, spans e log JSON |
| Testes | [Testes com BDD e arquivos .feature](testes-com-bdd.md) (v1.0.0) | o cenário primeiro, os steps e a cena sobre fakes |
| Testes | [Testes de contrato e de integração com BDD](testes-de-contrato-e-integracao-com-bdd.md) (v1.0.0) | o fake e o real no mesmo cenário, com containers |
| Testes | [Portões de arquitetura](portoes-de-arquitetura.md) (v1.0.0) | regras de estrutura cobradas por teste |

## ADRs citadas

| ADR | Título |
|---|---|
| ADR-001 | Despacho in-process de eventos de domínio com blinker |
| ADR-002 | Domain Driven Design nos módulos backend |
| ADR-003 | PostgreSQL, Flyway e acesso SQL-first com sqlc |
| ADR-004 | Unit of Work com transação nomeada, repositórios e leitores |
| ADR-005 | Métrica obrigatória de transações e queries |
| ADR-006 | Outbox transaction para eventos de integração |
| ADR-007 | Modelagem de estado por tipos |
| ADR-008 | Commands, queries e use cases na camada de aplicação |
| ADR-009 | Mappers e presenters nas periferias do domínio |
| ADR-010 | BDD com arquivos .feature como abordagem central dos testes de backend |
| ADR-011 | API REST com FastAPI documentada e validada em toda rota |
| ADR-012 | Observabilidade dos módulos de backend com OpenTelemetry |
| ADR-016 | Health checks com probes em paralelo |
| ADR-017 | API e job da outbox no mesmo módulo |

## O que ainda não tem ADR

A linha de comando, a tela Streamlit, o event loop de fundo e o health check só de liveness são escolhas do scaffold, sem ADR. Na configuração, o scaffold lê `LOG_DEBUG`, e a ADR-012 decide `LOG_LEVEL`. Os guidances desses assuntos dizem isso no "Por que foi criado" ou no passo afetado, e a lista completa está na seção 7 do [`stack.md`](../scafold/stack.md) do scaffold.

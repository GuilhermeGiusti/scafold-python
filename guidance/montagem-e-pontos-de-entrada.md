---
title: Montagem do processo e pontos de entrada
version: 1.0.0
---

# Montagem do processo e pontos de entrada

## Propósito

Depois de ler, você saberá montar um processo: a fundação compartilhada (métricas, camada de dados, observador, use cases e o manager de eventos), a montagem de cada borda e o ponto de entrada, na ordem certa de boot e de encerramento. Saberá também acrescentar um processo novo. A referência é [`bootstrap/composition.py`](../scafold/src/scafold/bootstrap/composition.py) e [`entrypoint/`](../scafold/entrypoint/).

## Problema que resolve

Sem um lugar só para juntar porta, adaptador e decorator, cada borda monta os use cases do seu jeito, um use case chega cru (sem medição e sem span), e o teste não consegue trocar as portas por fakes sem duplicar a montagem. E um boot fora de ordem conecta antes de validar a configuração, ou perde a telemetria pendente no encerramento.

## Por que foi criado

Pedido de 2026-11-18: guidances que ensinem a implementar seguindo o projeto de referência `../scafold`, para usar em outros repositórios. As decisões que o sustentam são a ADR-008 (Commands, queries e use cases na camada de aplicação), pelo decorator obrigatório, a ADR-012 (Observabilidade dos módulos de backend com OpenTelemetry), pela ordem do boot e pelos providers injetados, e a ADR-017 (API e job da outbox no mesmo módulo), pelos pontos de entrada lado a lado.

## Como implementar

### 1. A fundação, sem nenhuma borda

`build_foundation(settings=..., telemetry=..., clock=...)` roda uma vez por processo e devolve a `Foundation`: os adaptadores de métricas (`build_metrics_adapters`), a camada de dados (`open_persistence`), o `DomainEventManager` com os handlers (`build_event_manager`) e os use cases (`build_use_cases`). Ela não importa framework de borda e não conecta: o banco só é contatado no primeiro uso. `Foundation.close` fecha o pool, no mesmo event loop que o abriu. O relógio dos use cases é `utc_now`, injetado para os testes fixarem o instante.

### 2. Os use cases, montados sobre portas

`build_use_cases` recebe só portas (Unit of Work, repositório, leitor, gateway, gravador, dispatcher, relógio, observador) e devolve `UseCases`, com cada use case envolvido pelo decorator do seu contrato e tipado pelo contrato. É o mesmo código sobre o banco, em `build_foundation`, e sobre os fakes, em `build_scene`, em [`tests/support/scene.py`](../scafold/tests/support/scene.py). Um use case novo entra aqui e em `UseCases`.

### 3. A montagem de cada borda

Cada borda tem o seu módulo em `bootstrap/`, que recebe os use cases e devolve o objeto da borda:

| Borda | Montagem | Recebe |
|---|---|---|
| HTTP | `build_app`, em [`api.py`](../scafold/src/scafold/bootstrap/api.py) | `UseCases`, `Telemetry`, `expose_docs`, `on_shutdown` |
| Linha de comando | `build_parser`, `build_example_cli`, `run`, em [`cli.py`](../scafold/src/scafold/bootstrap/cli.py) | `UseCases` |
| Tela | `build_streamlit_process`, `build_example_page`, em [`streamlit_app.py`](../scafold/src/scafold/bootstrap/streamlit_app.py) | `UseCases` e o `run` do loop de fundo |
| Job da outbox | `build_outbox_job`, em [`outbox_job.py`](../scafold/src/scafold/bootstrap/outbox_job.py) | `JobSettings`, `Telemetry`, o pedido de parada |

`bootstrap/api.py` é o único módulo de `bootstrap/` que importa o FastAPI.

### 4. O ponto de entrada

Cada processo tem um arquivo em `entrypoint/`, com `run(environment) -> int` e `main()`, que só entrega `os.environ` (e `sys.argv`, na CLI) e sai com o código devolvido. A ordem do boot, em [`entrypoint/api.py`](../scafold/entrypoint/api.py):

1. a configuração, lida e validada antes de tudo; a recusa sai com código 1 numa linha da saída de erro;
2. o log estruturado, com o nível da configuração;
3. a telemetria;
4. a fundação e a borda, sem abrir conexão;
5. o servidor (ou o comando, ou o laço do job).

No encerramento, mesmo por erro, `telemetry.shutdown()` roda num `finally`, e o pool é fechado: pelo `lifespan` do app (`on_shutdown=foundation.close`), pelo `finally` de `_run_with_foundation` na CLI e por `OutboxJob.close` no job. Uma falha depois de o log existir sai em ERROR, com `logger.exception`.

| Arquivo | Processo | Comando |
|---|---|---|
| [`api.py`](../scafold/entrypoint/api.py) | API REST | `make api` |
| [`cli.py`](../scafold/entrypoint/cli.py) | um comando no shell | `make cli ARGS="..."` |
| [`streamlit_app.py`](../scafold/entrypoint/streamlit_app.py) | tela Streamlit | `make streamlit` |
| [`outbox_job.py`](../scafold/entrypoint/outbox_job.py) | job da outbox | `make outbox-job` |

### 5. Um processo novo

Uma montagem em `bootstrap/` que reaproveita `build_metrics_adapters`, `open_persistence` e o `UseCaseObserver` (como `build_outbox_job`), ou a `Foundation` inteira, e um arquivo em `entrypoint/` com a mesma ordem de boot e de encerramento. Se o processo tiver configuração própria, ele ganha o seu objeto, como `JobSettings` (veja [Configuração pelo ambiente e nível do log](configuracao-pelo-ambiente.md)), e um alvo no [`Makefile`](../scafold/Makefile).

### 6. Testar

Os cenários montam as bordas sobre a cena dos fakes: o app em `build_test_app` ([`tests/rest/conftest.py`](../scafold/tests/rest/conftest.py)), a CLI em [`test_cli.py`](../scafold/tests/edges/test_cli.py) e a tela em [`streamlit_scene.py`](../scafold/tests/support/streamlit_scene.py). A recusa de configuração do processo é exercitada pelo `run` de verdade, em [`cli.feature`](../scafold/tests/features/edges/cli.feature).

## Guidances relacionados

- [Commands, queries e use cases](commands-queries-e-use-cases.md) (v1.0.0): o decorator que `build_use_cases` aplica.
- [Telemetria com OpenTelemetry](telemetria-com-opentelemetry.md) (v1.0.0): os providers e os adaptadores que a montagem entrega.
- [Configuração pelo ambiente e nível do log](configuracao-pelo-ambiente.md) (v1.0.0): o primeiro passo do boot.
- [API REST documentada e validada](api-rest-documentada-e-validada.md), [Comando de linha de comando](linha-de-comando.md) e [Tela Streamlit](tela-streamlit.md) (v1.0.0): cada borda.

## Change log

| Versão | Data       | Pessoa           | Motivo                                                                                   |
|--------|------------|------------------|------------------------------------------------------------------------------------------|
| 1.0.0  | 2026-11-18 | Guilherme Giusti | Criação: ensinar a montar o processo e os pontos de entrada com o scaffold como referência |

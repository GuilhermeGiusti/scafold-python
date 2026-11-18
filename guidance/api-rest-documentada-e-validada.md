---
title: API REST documentada e validada
version: 1.0.0
---

# API REST documentada e validada

## Propósito

Depois de ler, você saberá escrever uma rota com FastAPI que cumpre duas regras sem exceção: explica no Swagger o que recebe, o que devolve e todos os status que pode devolver, e valida toda entrada na borda. Saberá também escrever a rota sem entrada (como o health check), registrar o controller na montagem, ligar o Swagger por configuração e escrever os testes que cobram as regras de todas as rotas. A referência é [`infrastructure/rest/`](../scafold/src/scafold/infrastructure/rest/) e [`bootstrap/api.py`](../scafold/src/scafold/bootstrap/api.py).

## Problema que resolve

Sem essas regras, quem consome a API precisa ler o código para saber o que enviar e o que pode voltar, e a documentação escrita à parte envelhece. Aqui o Swagger sai do próprio código da rota, e um teste falha quando uma rota deixa de documentar algo ou devolve um status que não documentou.

## Por que foi criado

Pedido de 2026-11-18: guidances que ensinem a implementar seguindo o projeto de referência `../scafold`, para usar em outros repositórios. A decisão que o sustenta é a ADR-011 (API REST com FastAPI documentada e validada em toda rota).

## Como implementar

### 1. Escreva o schema de entrada

Veja `CreateExampleRequest`, em [`example_schemas.py`](../scafold/src/scafold/infrastructure/rest/example_schemas.py), e a base `RequestSchema`, em [`shared/schemas.py`](../scafold/src/scafold/infrastructure/rest/shared/schemas.py).

- Herde de `RequestSchema`: campo desconhecido é recusado (`extra="forbid"`) e a docstring de cada campo vira a descrição dele (`use_attribute_docstrings`).
- Todo campo tem tipo, pelo menos uma restrição, um exemplo (`examples`) e a docstring logo abaixo dele.
- Texto, número e booleano são estritos (`StrictStr`, `StrictInt`, `StrictBool`); `UUID` e `datetime` não.
- O nome do contrato vai em `alias`: o atributo é `display_name`, o cliente envia `displayName`.
- Restrição de item de lista vai num alias simples com `Annotated` (`ItemName`), e não num `type`, para o Pydantic escrevê-la no próprio campo.

### 2. Escreva o schema de saída

Herde de `ResponseSchema`. Todo campo tem tipo real (`UUID`, `datetime`), exemplo e docstring; o nome do contrato vai em `serialization_alias`; uma lista tem schema próprio, como `ExampleListResponse`. Valor fechado vira `Literal`, como `CategoryText`.

### 3. Declare os parâmetros de path e de query

Cada parâmetro usa `Annotated` com `Path` ou `Query`, com `description`, `examples` e a restrição. Veja o alias `ExampleIdPath` e o `limit` de `ExampleController.list_all`, em [`example_controller.py`](../scafold/src/scafold/infrastructure/rest/example_controller.py). Use alias simples, e não `type`, para o FastAPI enxergar o `Annotated`.

### 4. Declare a rota

Toda rota passa a `add_api_route`, além do caminho, da função e do método:

| Argumento | O que diz no Swagger |
|---|---|
| `summary` | o que a rota faz, em poucas palavras |
| `description` | o que o consumidor precisa saber |
| `status_code` | o status do sucesso, quando não é 200 |
| `response_model` | o schema do corpo no sucesso (`None` no 204) |
| `response_description` | o que o sucesso significa |
| `responses` | `presenter.documented_errors(...)`, com os erros que o use case daquela rota levanta |

A função da rota chama o mapper, o use case e o presenter, sem `try`/`except`. Veja o construtor de `ExampleController`.

### 5. Documente os erros pela tabela do presenter

`ErrorEntry` e `ErrorPresenter` estão em [`shared/error_presenter.py`](../scafold/src/scafold/infrastructure/rest/shared/error_presenter.py); o presenter do agregado só declara `_ERRORS` e `PRESENTABLE` (veja [Mappers e presenters](mappers-e-presenters.md)).

- `present_error` usa a tabela para responder, e `documented_errors` usa a mesma tabela para montar o `responses`: o que o cliente recebe e o que o Swagger mostra não divergem.
- `documented_errors` sempre inclui o 500 e, na rota com entrada, o 422. Dois erros com o mesmo status juntam as descrições (os 409 da criação).
- Citar na rota um erro que não está na tabela faz a montagem do app falhar, de propósito.
- Erro de aplicação fora da tabela sai como 400 genérico, não documentado: o teste do passo 9 o acusa.
- `knows(error)` diz se o presenter conhece o erro; com mais de um agregado, a montagem entrega o erro ao presenter que o conhece.

### 6. A rota sem entrada: o health check

A rota sem parâmetro nem corpo não tem o que recusar e chama `documented_errors(validation=False)`, que deixa o 422 de fora. Veja `HealthController`, em [`health_controller.py`](../scafold/src/scafold/infrastructure/rest/health_controller.py), com `HealthResponse`: `GET /api/v1/health/check` responde 200 enquanto o processo atende, sem consultar dependências.

### 7. Monte o app

Em [`bootstrap/api.py`](../scafold/src/scafold/bootstrap/api.py), `build_app` recebe os use cases, a telemetria e `expose_docs`:

- registra os routers com o prefixo `API_PREFIX` (`/api/v1`);
- registra os exception handlers: `RequestValidationError` (`present_validation_error`, o 422 com `fields`), `HTTPException` (`present_http_error`), cada erro de `PRESENTABLE` e `Exception`, que dá o 500 sem detalhe;
- cria o app com `telemetry=framework_telemetry(telemetry)`. Nunca crie um `FastAPI(...)` sem o argumento `telemetry` (veja [Telemetria com OpenTelemetry](telemetria-com-opentelemetry.md));
- passa `docs_url` e `openapi_url` só quando `expose_docs` é verdadeiro. O documento existe sempre: `app.openapi()` não depende dessas rotas.

Um controller novo entra na tupla `controllers`, e o presenter dele em `presenters`.

### 8. Ligue o Swagger por configuração

`API_EXPOSE_DOCS`, lida em [`settings.py`](../scafold/src/scafold/bootstrap/settings.py), só liga com `true`; sem a variável, fica desligado. Os cenários estão em [`docs_exposure.feature`](../scafold/tests/features/rest/docs_exposure.feature).

### 9. Cobre as regras de todas as rotas por teste

As regras estão em [`tests/support/openapi_rules.py`](../scafold/tests/support/openapi_rules.py) e os cenários em [`openapi_contract.feature`](../scafold/tests/features/rest/openapi_contract.feature). Cada regra percorre todas as rotas do documento, então uma rota nova entra na cobrança sem mudar o teste:

| Regra | O que acusa |
|---|---|
| `without_summary_or_description` | rota sem resumo ou descrição |
| `without_success_model` | sucesso sem schema do corpo |
| `without_validation_and_defect_errors` | rota sem o 500, ou rota com entrada sem o 422 |
| `with_error_outside_the_error_format` | erro sem descrição, ou sem `code` e `message` |
| `with_undocumented_input_field` | campo de entrada sem descrição, exemplo ou restrição |
| `with_undocumented_output_field` | campo de saída sem descrição ou exemplo |
| `with_body_accepting_unknown_field` | corpo que aceita campo desconhecido |
| `with_body_converting_text` | corpo que aceita texto onde espera número ou booleano |

A aplicação escrita do jeito errado, [`undocumented_app.py`](../scafold/tests/support/undocumented_app.py), prova que cada regra acusa.

### 10. Prove que a rota só devolve o que documentou

O Schemathesis gera requisições válidas e inválidas a partir do OpenAPI e confere que o status está documentado e que o corpo segue o schema. Veja [`documented_behavior.feature`](../scafold/tests/features/rest/documented_behavior.feature), com a tag `@fuzz`, e [`test_documented_behavior.py`](../scafold/tests/rest/test_documented_behavior.py): `has_input` pula a rota sem entrada no modo inválido, e a checagem `positive_data_acceptance` fica de fora porque o modo estrito recusa `5.0` de propósito.

### 11. Escreva os cenários de comportamento

Um cenário por status documentado de cada rota e uma linha por entrada inválida, sobre o app montado com os fakes (`build_test_app`, em [`tests/rest/conftest.py`](../scafold/tests/rest/conftest.py)). Veja [`example_api.feature`](../scafold/tests/features/rest/example_api.feature) e [`health_check.feature`](../scafold/tests/features/rest/health_check.feature).

## Quando não se aplica

- **Regra de negócio.** A validação da borda cobre tipo, formato e restrição; quem diz se o valor é válido para o negócio é o domínio.
- **Rotas que o framework cria**, como `/docs` e `/openapi.json`, não entram no documento nem na cobrança.
- **Health check com probes.** A ADR-016 (Health checks com probes em paralelo) decide `/live` e `/ready` com probes; a rota da referência é só de liveness, e alinhar as duas formas é decisão em aberto.

## Guidances relacionados

- [Mappers e presenters](mappers-e-presenters.md) (v1.0.0): o request mapper e o presenter que esta rota usa.
- [Commands, queries e use cases](commands-queries-e-use-cases.md) (v1.0.0): os use cases que o controller recebe.
- [Telemetria com OpenTelemetry](telemetria-com-opentelemetry.md) (v1.0.0): o argumento `telemetry` do app.
- [Testes com BDD e arquivos .feature](testes-com-bdd.md) (v1.0.0): como escrever os `.feature` e os steps.

## Change log

| Versão | Data       | Pessoa           | Motivo                                                                                   |
|--------|------------|------------------|------------------------------------------------------------------------------------------|
| 1.0.0  | 2026-11-18 | Guilherme Giusti | Criação: ensinar a escrever rotas documentadas e validadas, com o health check, usando o scaffold como referência |

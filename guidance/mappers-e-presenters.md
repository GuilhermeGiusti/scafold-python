---
title: Mappers e presenters
version: 1.0.0
---

# Mappers e presenters

## Propósito

Depois de ler, você saberá escrever as classes que traduzem dados nas periferias do domínio: o mapper de entrada de cada borda (HTTP, linha de comando, tela), o presenter de cada borda, o mapper de persistência e o mapper anti-corrupção de um serviço externo, com o adaptador que o usa. Saberá onde cada uma mora, como se chama, quem a chama e onde não se escreve mapper. A referência são as pastas `mappers/` e `presenters/` de [`infrastructure/`](../scafold/src/scafold/infrastructure/).

## Problema que resolve

Sem essas classes, os modelos de fora entram no lado de dentro e o sujam: o use case passa a conhecer o schema HTTP, o agregado ganha a forma da tabela e o domínio passa a falar o vocabulário de um fornecedor. A partir daí, renomear um campo da API, trocar uma coluna ou trocar de fornecedor vira mudança na aplicação ou no domínio. Com um mapper em cada fronteira, cada mudança altera só a classe que traduz.

## Por que foi criado

Pedido de 2026-11-18: guidances que ensinem a implementar seguindo o projeto de referência `../scafold`, para usar em outros repositórios. A decisão que o sustenta é a ADR-009 (Mappers e presenters nas periferias do domínio).

## Como implementar

### 1. Localize a fronteira, a pasta e o nome

| Travessia | Nome | Pasta | Na referência |
|---|---|---|---|
| schema HTTP para command ou query | `<Agregado>RequestMapper` | `infrastructure/rest/mappers/` | `ExampleRequestMapper` |
| argumentos da linha de comando para command ou query | `<Agregado>ArgumentsMapper` | `infrastructure/cli/mappers/` | `ExampleArgumentsMapper` |
| valores do formulário para command | `<Agregado>FormMapper` | `infrastructure/streamlit/mappers/` | `ExampleFormMapper` |
| DTO de saída e erro para a resposta da borda | `<Agregado>Presenter`, `<Agregado>CliPresenter`, `<Agregado>PagePresenter` | `.../presenters/` da borda | `ExamplePresenter`, `ExampleCliPresenter`, `ExamplePagePresenter` |
| agregado para row, e row para agregado | `<Agregado>RowMapper` | `infrastructure/persistence/<contexto>/mappers/` | `ExampleRowMapper` |
| payload do fornecedor para tipo do domínio, e o inverso | `<Conceito>PayloadMapper` | `infrastructure/external/mappers/` | `CategoryPayloadMapper` |

Todas seguem as mesmas regras: são classes, com um método por tradução; moram do lado de fora, no adaptador que as usa, e o domínio e a aplicação nunca as importam; só traduzem (não validam regra, não fazem I/O, não guardam estado); chegam pelo construtor de quem as usa. O use case não recebe mapper nem presenter.

### 2. Mapper de entrada

Um método por pedido, que recebe o que veio da borda e devolve o input do use case. É aqui que o nome do contrato vira o nome da aplicação: `displayName` vira `label`. Veja [`example_request_mapper.py`](../scafold/src/scafold/infrastructure/rest/mappers/example_request_mapper.py), [`example_arguments_mapper.py`](../scafold/src/scafold/infrastructure/cli/mappers/example_arguments_mapper.py) e [`example_form_mapper.py`](../scafold/src/scafold/infrastructure/streamlit/mappers/example_form_mapper.py), que transforma o texto de uma linha por item em tupla. O mapper não rejeita valor pela regra de negócio: um nome em branco passa por ele, e quem o recusa é o domínio.

### 3. Presenter

O presenter decide a apresentação: os nomes do contrato, o formato, o texto de cada erro. O texto do erro é do presenter, nunca `str(error)`, para o detalhe interno não vazar.

- **REST**: `ExamplePresenter`, em [`example_presenter.py`](../scafold/src/scafold/infrastructure/rest/presenters/example_presenter.py), herda de `ErrorPresenter` e declara `_ERRORS`, `PRESENTABLE` e os métodos de saída (`present`, `present_list`, `present_created`), com `_CATEGORY_TEXT` para o texto da categoria. A tabela de erros também documenta as rotas: veja [API REST documentada e validada](api-rest-documentada-e-validada.md).
- **Linha de comando**: `ExampleCliPresenter`, em [`example_cli_presenter.py`](../scafold/src/scafold/infrastructure/cli/presenters/example_cli_presenter.py), devolve JSON, e o erro esperado sai com código e texto.
- **Tela**: `ExamplePagePresenter`, em [`example_page_presenter.py`](../scafold/src/scafold/infrastructure/streamlit/presenters/example_page_presenter.py), com os nomes das colunas (`COLUMNS`) e o texto de cada erro.

Erro de domínio que a borda apresenta entra em `PRESENTABLE` e na tabela; erro de aplicação já entra pela base `ApplicationError`. Erro fora da tabela é defeito e sobe.

### 4. Mapper de persistência

Tem as duas direções, guarda o detalhe de armazenamento (o código de uma letra da categoria) e reconstrói pelo construtor do agregado. Veja `ExampleRowMapper`, em [`example_row_mapper.py`](../scafold/src/scafold/infrastructure/persistence/bounded_context_example/mappers/example_row_mapper.py). O repositório o recebe pelo construtor.

### 5. Mapper anti-corrupção e o adaptador do serviço externo

- A porta fica em `applications/ports/` e fala no vocabulário do domínio: `ICategoryGateway`, em [`category_gateway.py`](../scafold/src/scafold/applications/ports/category_gateway.py).
- O mapper monta o pedido do fornecedor (`to_request_payload`) e traduz a resposta (`to_category`). O vocabulário do fornecedor fica na tabela `_CATEGORY_BY_TIER`. Veja [`category_payload_mapper.py`](../scafold/src/scafold/infrastructure/external/mappers/category_payload_mapper.py).
- Termo desconhecido não vira valor por palpite: o mapper levanta `UnmappedPayload`, erro próprio de infraestrutura em [`external/errors/`](../scafold/src/scafold/infrastructure/external/errors/unmapped_payload.py).
- O adaptador, `ExternalCategoryGateway`, em [`external_category_gateway.py`](../scafold/src/scafold/infrastructure/external/external_category_gateway.py), registra a falha no log e a conta em `external_translation_errors_total{gateway}`, pela porta `ITranslationErrorMetrics`, antes de relançar. O rótulo é a constante `GATEWAY_NAME`; o termo do fornecedor nunca vira rótulo.
- O cliente do fornecedor, na referência, é [`fake_category_api.py`](../scafold/src/scafold/infrastructure/external/fake_category_api.py). Num projeto real ele é o cliente HTTP, e o resto do adaptador não muda.

### 6. Testar

Os mappers de persistência e anti-corrupção têm cenários em [`mappers.feature`](../scafold/tests/features/infrastructure/mappers.feature): a ida e volta do agregado, o código gravado da categoria, a tradução do `tier` e o termo desconhecido contado com o nome do adaptador. Os presenters e mappers de borda são exercitados pelos cenários de cada borda, e o portão de [`boundaries.feature`](../scafold/tests/features/architecture/boundaries.feature) prova que o lado de dentro não os importa.

## Quando não se aplica

- **Entre o use case e o domínio.** Construir um id tipado a partir do command é o domínio validando, e não tradução entre modelos.
- **Do agregado para o DTO de saída.** O mapeamento fica no próprio DTO (`ExampleView.from_aggregate`), sem classe mapper.

## Guidances relacionados

- [Commands, queries e use cases](commands-queries-e-use-cases.md) (v1.0.0): o input que o mapper produz e o DTO que o presenter recebe.
- [API REST documentada e validada](api-rest-documentada-e-validada.md) (v1.0.0): a tabela de erros que responde e documenta.
- [Repositório e leitor sobre o querier do sqlc](repositorio-e-leitor-sobre-sqlc.md) (v1.0.0): o adaptador onde o mapper de persistência entra.
- [Comando de linha de comando](linha-de-comando.md) (v1.0.0) e [Tela Streamlit](tela-streamlit.md) (v1.0.0): as outras bordas.

## Change log

| Versão | Data       | Pessoa           | Motivo                                                                                   |
|--------|------------|------------------|------------------------------------------------------------------------------------------|
| 1.0.0  | 2026-11-18 | Guilherme Giusti | Criação: ensinar a escrever mappers e presenters em todas as bordas com o scaffold como referência |

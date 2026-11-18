---
title: Tela Streamlit
version: 1.0.0
---

# Tela Streamlit

## Propósito

Depois de ler, você saberá escrever uma página Streamlit que chama os mesmos use cases da API, montar o processo uma vez por `st.cache_resource` e chamar use case assíncrono a partir do script síncrono sem trocar de event loop. Saberá também testar a página com o executor de testes do Streamlit. A referência é [`infrastructure/streamlit/`](../scafold/src/scafold/infrastructure/streamlit/), [`bootstrap/streamlit_app.py`](../scafold/src/scafold/bootstrap/streamlit_app.py) e [`entrypoint/streamlit_app.py`](../scafold/entrypoint/streamlit_app.py).

## Problema que resolve

O Streamlit reexecuta o script inteiro a cada interação e é síncrono. Montar a camada de dados dentro do script abriria um pool a cada clique, e chamar `asyncio.run` a cada use case criaria um event loop novo por chamada: o pool do banco fica preso ao loop que abriu as conexões, e a segunda chamada falharia. A página também não pode ter regra: ela é uma borda, com mapper e presenter.

## Por que foi criado

Pedido de 2026-11-18: guidances que ensinem a implementar seguindo o projeto de referência `../scafold`, para usar em outros repositórios. Nenhuma ADR decide a borda Streamlit: ela e o event loop de fundo são escolhas do scaffold, pendentes de decisão. Os mappers e presenters seguem a ADR-009 (Mappers e presenters nas periferias do domínio).

## Como implementar

### 1. Monte o processo uma vez

`build_streamlit_process`, em [`bootstrap/streamlit_app.py`](../scafold/src/scafold/bootstrap/streamlit_app.py), lê a configuração, configura o log, monta a telemetria e a fundação e cria o `BackgroundLoop`, e devolve um `StreamlitProcess`. O ponto de entrada o guarda com `@st.cache_resource` (função `_process`, em [`entrypoint/streamlit_app.py`](../scafold/entrypoint/streamlit_app.py)): vive o processo inteiro, e a referência forte mantém o `DomainEventManager` vivo. A configuração recusada aparece na tela com `st.error`, seguida de `st.stop()`.

### 2. Chame use case assíncrono pelo loop de fundo

`BackgroundLoop`, em [`background_loop.py`](../scafold/src/scafold/bootstrap/background_loop.py), roda um event loop numa thread própria; `run(corrotina)` a executa nesse loop e devolve o resultado, ou levanta o erro dela. Todo use case do processo roda no mesmo loop, então o pool do banco é sempre o mesmo. A página recebe esse `run` pela porta `Runner`, em [`example_page.py`](../scafold/src/scafold/infrastructure/streamlit/example_page.py); nos testes, sobre os fakes, `asyncio.run` basta.

### 3. Escreva a página

`ExamplePage` recebe os use cases tipados pelo contrato, o `run`, o `ExampleFormMapper` e o `ExamplePagePresenter`, e desenha a tela em `render`. Cada widget tem `key`, o que deixa o teste encontrá-lo. A ação de um botão traduz os valores pelo mapper, chama o use case pelo `run` e mostra o resultado pelo presenter; o erro esperado (`PRESENTABLE` do presenter) vira `st.error` com o texto do presenter, e o defeito sobe. Veja `ExamplePage._create_example` e `ExamplePage._archive_example`. A página é montada a cada execução do script por `build_example_page`, barata.

### 4. Acrescente uma página

Uma classe em `infrastructure/streamlit/` com o seu mapper e presenter, montada numa função em `bootstrap/streamlit_app.py` e chamada pelo ponto de entrada. Para várias páginas, o ponto de entrada escolhe qual renderizar.

### 5. Testar

O executor `AppTest` roda a página de verdade, reexecutando o script a cada interação. A função `page_over_fakes`, em [`test_streamlit_page.py`](../scafold/tests/edges/test_streamlit_page.py), é copiada como texto pelo executor, então os imports ficam dentro dela; ela chama `render_over_fakes`, em [`tests/support/streamlit_scene.py`](../scafold/tests/support/streamlit_scene.py), que guarda a cena dos fakes em `st.session_state`. Os widgets são achados pela `key`, e o resultado é lido em `success`, `error`, `info` e `dataframe`. Os cenários estão em [`streamlit_page.feature`](../scafold/tests/features/edges/streamlit_page.feature). A raiz do projeto entra no caminho de import pelo `pythonpath` do [`pyproject.toml`](../scafold/pyproject.toml).

## Quando não se aplica

O Streamlit não tem gancho de encerramento: a telemetria pendente e o pool não são fechados quando o processo para. Um processo que precisa desse encerramento deve ser outra borda.

## Guidances relacionados

- [Mappers e presenters](mappers-e-presenters.md) (v1.0.0): o mapper do formulário e o presenter da tela.
- [Montagem do processo e pontos de entrada](montagem-e-pontos-de-entrada.md) (v1.0.0): a fundação que o processo monta.
- [Testes com BDD e arquivos .feature](testes-com-bdd.md) (v1.0.0): os cenários da tela.

## Change log

| Versão | Data       | Pessoa           | Motivo                                                                                   |
|--------|------------|------------------|------------------------------------------------------------------------------------------|
| 1.0.0  | 2026-11-18 | Guilherme Giusti | Criação: ensinar a escrever uma tela Streamlit sobre os use cases com o scaffold como referência |

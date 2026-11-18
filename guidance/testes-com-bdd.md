---
title: Testes com BDD e arquivos .feature
version: 1.0.0
---

# Testes com BDD e arquivos .feature

## Propósito

Depois de ler, você saberá escrever um teste partindo do comportamento: primeiro o cenário, num `.feature`, e depois os steps em Python que o executam com `pytest-bdd`. Saberá ligar o arquivo ao `pytest`, passar dados do cenário para os steps, tratar o erro esperado, montar os use cases sobre fakes e rodar código async. A referência é [`tests/`](../scafold/tests/) e a configuração em [`pyproject.toml`](../scafold/pyproject.toml).

## Problema que resolve

Sem o `.feature`, o cenário aprovado é reescrito à mão como função de teste, e as duas versões divergem. O teste passa a ser lido no vocabulário do código, e não no do negócio, e tende a descrever a estrutura interna, quebrando a cada refatoração. Com o `.feature`, o texto que se lê é o que se executa, e ele só fala do que é observável.

## Por que foi criado

Pedido de 2026-11-18: guidances que ensinem a implementar seguindo o projeto de referência `../scafold`, para usar em outros repositórios. A decisão que o sustenta é a ADR-010 (BDD com arquivos .feature como abordagem central dos testes de backend).

## Como implementar

### 1. Prepare o projeto

No [`pyproject.toml`](../scafold/pyproject.toml):

- o grupo `dev` traz `pytest`, `pytest-bdd`, `pytest-randomly` (ordem aleatória: cenário dependente de outro falha cedo), `pytest-cov` e `mypy`;
- `bdd_features_base_dir = "tests/features"`: o módulo de teste cita o `.feature` pelo caminho a partir dali;
- `addopts` liga `--strict-markers` e a cobertura, reportada e sem mínimo;
- `markers` registra toda tag usada nos `.feature` (`domain`, `contract`, `integration`, `fuzz`); tag não registrada derruba a coleta;
- `filterwarnings` transforma `RuntimeWarning` em erro (uma corrotina que ninguém aguardou);
- `[tool.mypy]` é `strict` e inclui `tests`.

### 2. Escreva o cenário antes do código

O `.feature` fica em `tests/features/<camada>/<assunto>.feature` e começa com `# language: pt`. As partes: `Funcionalidade` (uma por arquivo), `Regra` (a regra de negócio, como afirmação), `Contexto` (passos `Dado` que rodam antes de cada cenário), `Cenário`, `Esquema do Cenário` com `Exemplos` (uma linha por caso), `Dado`, `Quando` (uma ação), `Então`, `E` e `@tag`. Veja [`example.feature`](../scafold/tests/features/domain/example.feature) e [`create_example.feature`](../scafold/tests/features/applications/create_example.feature).

### 3. Escreva passos que falam do negócio

- Dados concretos: `"Relatório"`, `2 itens`, `"2026-11-19T08:30:00+00:00"`.
- Os limites viram linhas de `Exemplos` (o nome de 1, de 64 e de 65 caracteres).
- Dependência descrita como estado, e não como mock (`Dado o broker falhando de forma transitória`).
- O que não deve acontecer também é passo (`E nenhuma transação foi aberta`).
- A recusa diz o motivo na língua do negócio: `Então a operação é recusada por nome já usado`, nunca o nome da classe do erro.
- Célula vazia de tabela não casa com `"{nome}"`: escreva um passo próprio para o vazio, como `crio um Example com um nome só de espaços`.

### 4. Ligue o `.feature` ao pytest

Cada `.feature` tem um `tests/<camada>/test_<assunto>.py` com `scenarios("<camada>/<assunto>.feature")` no topo, as fixtures e os steps; não há funções `test_*`. Veja [`test_example.py`](../scafold/tests/domain/test_example.py).

### 5. Implemente os steps

Um step é uma função decorada com `given`, `when` ou `then`, ligada ao passo pelo texto. Texto com dados usa `parsers.parse`, com `{nome}` virando argumento (`{count:d}` vira `int`); a conversão para tipo de domínio é do step. `E` usa o decorador da palavra-chave que repete. As funções de step se chamam `_`. Steps usados por vários módulos ficam no `conftest.py` da pasta: os da aplicação em [`tests/applications/conftest.py`](../scafold/tests/applications/conftest.py), os da API em [`tests/rest/conftest.py`](../scafold/tests/rest/conftest.py).

### 6. Passe estado entre os passos com `target_fixture`

Um `given` ou `when` com `target_fixture="nome"` publica o que devolve como a fixture `nome`, e o step seguinte a recebe pelo parâmetro. Cada cenário começa com as fixtures zeradas. O `Então` só lê e faz `assert`.

### 7. Trate o erro esperado como resultado

O `Quando` executa a ação e devolve em `outcome` o resultado ou o erro esperado; o `except` lista só os erros esperados daquela ação, e qualquer outro sobe como defeito. Não use `except Exception` nem `pytest.raises` no `Quando`. O `Então` da recusa é um só, em [`tests/conftest.py`](../scafold/tests/conftest.py): `a operação é recusada por {reason}`, que compara o tipo exato de `outcome` com a tabela `REASONS`. Um erro novo ganha a sua frase em `REASONS`.

### 8. Fakes, a cena e código async

- Os fakes são código normal, sem framework de mock, em [`tests/support/fakes.py`](../scafold/tests/support/fakes.py). Um fake que pode ser uma função é uma função; os de porta são classes pequenas (`KeywordCategoryGateway`, `ScriptedDispatcher`).
- A cena monta os use cases do processo sobre os fakes, com o mesmo `build_use_cases` da produção: a fixture `scene`, sobre `build_scene`, em [`tests/support/scene.py`](../scafold/tests/support/scene.py). O cenário de aplicação exercita o use case já decorado.
- Os steps são síncronos. Para chamar código async, o step recebe a fixture `run`, que abre um `asyncio.Runner` por cenário, e chama `run(use_case.execute(...))`.
- Um `Dado` troca o fake padrão publicando outro objeto na mesma fixture (veja `o broker falhando de forma permanente`, em [`test_outbox_drain.py`](../scafold/tests/applications/test_outbox_drain.py)).
- As fixtures `autouse` de `tests/conftest.py` isolam o sinal global do `blinker` e o logger raiz entre cenários.

### 9. Marque com tags e rode

| Comando | O que roda |
|---|---|
| `uv run pytest -m "not integration"` | tudo o que roda sem Docker |
| `uv run pytest -m domain` | só as regras puras do domínio |
| `uv run pytest -k "arquivado"` | os cenários cujo título contém o texto |
| `uv run mypy` | a checagem de tipos, steps incluídos |

## Quando não se aplica

Testes de contrato e de integração também nascem de um `.feature`, mas pedem banco real e fixture parametrizada: siga [Testes de contrato e de integração com BDD](testes-de-contrato-e-integracao-com-bdd.md).

## Guidances relacionados

- [Testes de contrato e de integração com BDD](testes-de-contrato-e-integracao-com-bdd.md) (v1.0.0): o mesmo cenário contra o fake e contra o adaptador real.
- [Portões de arquitetura](portoes-de-arquitetura.md) (v1.0.0): os cenários que cobram regras de estrutura.
- [Commands, queries e use cases](commands-queries-e-use-cases.md) (v1.0.0): os use cases que a cena monta.

## Change log

| Versão | Data       | Pessoa           | Motivo                                                                                   |
|--------|------------|------------------|------------------------------------------------------------------------------------------|
| 1.0.0  | 2026-11-18 | Guilherme Giusti | Criação: ensinar testes com BDD e arquivos `.feature` com o scaffold como referência     |

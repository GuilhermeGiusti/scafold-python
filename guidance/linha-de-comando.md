---
title: Comando de linha de comando
version: 1.0.0
---

# Comando de linha de comando

## Propósito

Depois de ler, você saberá expor um use case como comando de shell: declarar o comando e os argumentos, traduzi-los no input do use case, apresentar o resultado em JSON e devolver o código de saída certo. A referência é [`infrastructure/cli/`](../scafold/src/scafold/infrastructure/cli/), [`bootstrap/cli.py`](../scafold/src/scafold/bootstrap/cli.py) e [`entrypoint/cli.py`](../scafold/entrypoint/cli.py).

## Problema que resolve

Um script que monta a camada de dados por conta própria e chama o repositório direto pula as regras do use case, a medição e o span, e cada script novo repete a configuração. Aqui a linha de comando é uma borda como a HTTP: os mesmos use cases, a mesma montagem e o mesmo boot, e só o mapper e o presenter mudam.

## Por que foi criado

Pedido de 2026-11-18: guidances que ensinem a implementar seguindo o projeto de referência `../scafold`, para usar em outros repositórios. Nenhuma ADR decide a borda de linha de comando: o uso do `argparse` e os códigos de saída são escolhas do scaffold, pendentes de decisão. Os mappers e presenters seguem a ADR-009 (Mappers e presenters nas periferias do domínio).

## Como implementar

### 1. Declare os comandos sem depender de use case

`ExampleCli.add_commands`, em [`example_cli.py`](../scafold/src/scafold/infrastructure/cli/example_cli.py), declara os subcomandos e os argumentos. Tipo e restrição são conferidos pelo `argparse` na borda: o `--id` usa `type=UUID`, e o `--limit` usa a função `_limit`, que recusa fora de 1 a 100 com `argparse.ArgumentTypeError`. Por ser estático, o parser existe sem configuração, e `--help` funciona sem ambiente. `build_parser`, em [`bootstrap/cli.py`](../scafold/src/scafold/bootstrap/cli.py), junta os comandos de cada agregado.

### 2. Traduza e apresente

`ExampleCli.execute` escolhe o comando com `match`, traduz os argumentos pelo `ExampleArgumentsMapper` e devolve o texto do `ExampleCliPresenter` (veja [Mappers e presenters](mappers-e-presenters.md)). A classe recebe os use cases pelo construtor, tipados pelo contrato, como o controller REST.

### 3. Rode o comando e decida o código de saída

`execute`, em [`bootstrap/cli.py`](../scafold/src/scafold/bootstrap/cli.py), roda um comando já validado: o resultado vai para a saída padrão; o erro esperado (`ExampleCli.presents`) vai como JSON para a saída de erro; o defeito sobe. Os códigos são constantes do módulo:

| Constante | Código | Quando |
|---|---|---|
| `EXIT_OK` | 0 | o comando terminou bem |
| `EXIT_FAILURE` | 1 | configuração recusada, ou defeito registrado no log |
| `EXIT_USAGE` | 2 | argumento inválido, recusado pelo `argparse` |
| `EXIT_REFUSED` | 3 | o pedido foi recusado por uma regra |

### 4. A ordem do boot

`run(argv, environment, stdout=..., stderr=...)` segue a ordem: argumentos, configuração (recusa com código 1, numa linha da saída de erro), log, telemetria, e então o comando dentro de `asyncio.run`, que monta a fundação, executa e fecha o pool no mesmo event loop (`_run_with_foundation`). `telemetry.shutdown()` fica num `finally`. O ponto de entrada, [`entrypoint/cli.py`](../scafold/entrypoint/cli.py), só entrega `sys.argv` e `os.environ` a `run`.

### 5. Acrescente um comando

Declare o subcomando em `add_commands`, o método no mapper de argumentos, o caso em `execute` e o método de saída no presenter. Um agregado novo ganha a sua classe de CLI, que entra em `build_parser` e em `build_example_cli` (ou numa função irmã).

### 6. Testar

O comando roda sobre os fakes, com o mesmo parser e a mesma borda (`over_fakes`), e o processo sem configuração roda pelo `run` de verdade. Veja [`cli.feature`](../scafold/tests/features/edges/cli.feature) e [`test_cli.py`](../scafold/tests/edges/test_cli.py).

## Guidances relacionados

- [Commands, queries e use cases](commands-queries-e-use-cases.md) (v1.0.0): os use cases que a borda chama.
- [Mappers e presenters](mappers-e-presenters.md) (v1.0.0): o mapper de argumentos e o presenter da CLI.
- [Montagem do processo e pontos de entrada](montagem-e-pontos-de-entrada.md) (v1.0.0): a fundação que o comando monta.
- [Configuração pelo ambiente e nível do log](configuracao-pelo-ambiente.md) (v1.0.0): a recusa de configuração.

## Change log

| Versão | Data       | Pessoa           | Motivo                                                                                   |
|--------|------------|------------------|------------------------------------------------------------------------------------------|
| 1.0.0  | 2026-11-18 | Guilherme Giusti | Criação: ensinar a expor use cases como comando de shell com o scaffold como referência  |

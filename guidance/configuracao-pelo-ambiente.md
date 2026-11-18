---
title: Configuração pelo ambiente e nível do log
version: 1.0.0
---

# Configuração pelo ambiente e nível do log

## Propósito

Depois de ler, você saberá ler a configuração do processo do ambiente, uma vez, num objeto imutável; escrever as regras de cada variável (obrigatória, interruptor, formato, inteiro positivo); recusar o boot sem repetir o valor recebido; e controlar o nível do log com `LOG_DEBUG`. A referência é [`bootstrap/settings.py`](../scafold/src/scafold/bootstrap/settings.py) e [`bootstrap/job_settings.py`](../scafold/src/scafold/bootstrap/job_settings.py).

## Problema que resolve

Com `os.environ` lido em qualquer lugar, um teste não consegue montar a configuração que quer, e duas partes do código interpretam a mesma variável de jeitos diferentes. Um interruptor que aceita `0` ou `True` adivinha a intenção e faz o processo subir fazendo o contrário. E a mensagem de recusa que repete o valor recebido é o caminho mais curto para um segredo (a senha da `DATABASE_URL`) chegar ao log de um orquestrador.

## Por que foi criado

Pedido de 2026-11-18: guidances que ensinem a implementar seguindo o projeto de referência `../scafold`, para usar em outros repositórios. As regras da configuração e do log vêm da ADR-012 (Observabilidade dos módulos de backend com OpenTelemetry), com uma divergência registrada no passo 4: o scaffold usa `LOG_DEBUG`, como pedido, e a ADR decide `LOG_LEVEL`.

## Como implementar

### 1. Só a configuração lê o ambiente

O ponto de entrada entrega `os.environ` a `Settings.from_environment`, e o resto do processo recebe `Settings` por parâmetro. Nenhum outro módulo lê o ambiente, e o portão de [`boundaries.feature`](../scafold/tests/features/architecture/boundaries.feature) acusa quem ler. `Settings` é um `@dataclass(frozen=True, slots=True, kw_only=True)`, com o segredo fora do `repr` (`database_url: str = field(repr=False)`).

### 2. As regras de cada variável

Cada regra é uma função do módulo, reaproveitada por `Settings` e `JobSettings`, com a mesma mensagem:

| Função | Regra |
|---|---|
| `optional` | ausente ou só com espaços é o mesmo caso: `None` |
| `required` | ausente é recusa |
| `switch` | só `true` e `false`, em minúsculas; ausente vale o padrão informado |
| `database_url` | obrigatória e só com o esquema `postgresql://`; quem escolhe o driver é a camada de dados |
| `outbox_dispatcher` | obrigatória e dentro de `KNOWN_DISPATCHERS` |
| `otlp_endpoints` | o endereço de cada sinal vence o endereço base; sem nenhum, `DEFAULT_OTLP_ENDPOINT` |
| `positive_integer` | só dígitos ASCII e maior que zero; ausente vale o padrão |

O nome de cada variável é uma constante do módulo (`SERVICE_NAME_VARIABLE`, `LOG_DEBUG_VARIABLE`...). A recusa é `ConfigurationError`, cita a variável e o formato esperado, e nunca o valor.

### 3. A recusa sai antes do log

O ponto de entrada captura `ConfigurationError`, escreve a mensagem numa linha da saída de erro e sai com código 1, antes de configurar o log, de montar a telemetria e de abrir qualquer conexão. Veja `run`, em [`entrypoint/api.py`](../scafold/entrypoint/api.py); a CLI, o job e a tela fazem o mesmo.

### 4. O nível do log com `LOG_DEBUG`

`LOG_DEBUG` é um interruptor que nasce desligado. `Settings.log_level` devolve `DEFAULT_LOG_LEVEL` (WARNING) sem ele e `DEBUG_LOG_LEVEL` (DEBUG) com `true`, e o ponto de entrada o passa a `configure_logging`, que o aplica no logger raiz, valendo também para as bibliotecas de terceiros:

| `LOG_DEBUG` | O que aparece |
|---|---|
| ausente ou `false` | WARNING e ERROR: falha de use case, defeito, disparo pulado do cron |
| `true` | tudo, a partir de DEBUG: início e fim de use case, medições escritas no log, saída dos handlers, resumo do ciclo da outbox |

Para isso funcionar, o código escreve cada registro no nível certo: o que é rotina sai em DEBUG (`UseCaseObserver`, os adaptadores de log das métricas, `OutboxDrainUseCase`), e a falha sai com `log.exception`.

**Divergência em aberto.** A ADR-012 (DO12.1) decide a variável `LOG_LEVEL`, com `DEBUG`, `INFO`, `WARNING` e `ERROR`, padrão `WARNING`. As duas formas concordam no padrão e no que sai em DEBUG; diferem no nome da variável e em `LOG_LEVEL=ERROR`, que esconde os avisos. Qual das duas vale num repositório novo é uma decisão a registrar antes de copiar este passo.

### 5. Uma configuração por processo

A API, a CLI e a tela usam `Settings`. O job usa `JobSettings`, um objeto próprio: a API não lê as variáveis do job, e o job não lê `API_EXPOSE_DOCS`. As variáveis compartilhadas têm o mesmo nome de campo e passam pelas mesmas funções. As duas cumprem `TelemetrySettings`, então a telemetria é montada pela mesma função.

### 6. Uma variável nova

Uma constante com o nome, uma regra (função existente ou nova, com a mesma forma de recusa), um campo em `Settings` ou `JobSettings`, e uma linha comentada no [`.env.example`](../scafold/.env.example). Nenhum outro módulo lê a variável: o valor segue por parâmetro.

### 7. Testar

A configuração é uma função de um dicionário e se testa sem processo: [`settings.feature`](../scafold/tests/features/bootstrap/settings.feature) cobre `LOG_DEBUG`, os interruptores, as obrigatórias e a recusa sem repetir o valor, e [`log_level.feature`](../scafold/tests/features/bootstrap/log_level.feature) cobre os níveis que aparecem no log.

## Guidances relacionados

- [Telemetria com OpenTelemetry](telemetria-com-opentelemetry.md) (v1.0.0): o log estruturado e os sinais que as variáveis ligam.
- [Montagem do processo e pontos de entrada](montagem-e-pontos-de-entrada.md) (v1.0.0): a ordem do boot.
- [Portões de arquitetura](portoes-de-arquitetura.md) (v1.0.0): o teste que reprova quem lê o ambiente.

## Change log

| Versão | Data       | Pessoa           | Motivo                                                                                   |
|--------|------------|------------------|------------------------------------------------------------------------------------------|
| 1.0.0  | 2026-11-18 | Guilherme Giusti | Criação: ensinar a ler a configuração do ambiente e controlar o log com `LOG_DEBUG`, com o scaffold como referência |

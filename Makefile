# Scaffold: stack local, migrations, geração com sqlc, processos e portões.
#
# Tudo roda a partir desta pasta. `bash` porque as receitas usam `[[ ]]`. Numa máquina sem GNU make,
# rode o comando da receita direto.

SHELL := bash

# A versão do sqlc é fixada e conferida antes de gerar: duas versões gerariam código diferente.
SQLC_VERSION := 1.31.1

POSTGRES_PORT ?= 5432
export POSTGRES_PORT

# O banco contra o qual `sqlc vet` prepara cada query. O padrão é o Postgres do compose.
SQLC_DATABASE_URI ?= postgresql://app:app@localhost:$(POSTGRES_PORT)/app?sslmode=disable

COMPOSE := docker compose -f docker-compose.yml

.PHONY: help install stack-up stack-down migrate-up migrate-info generate sqlc-check sqlc-vet \
        api cli streamlit outbox-job typecheck test-unit test check

help:
	@echo "  make install       instala as dependencias (uv sync)"
	@echo "  make stack-up      sobe Postgres, RabbitMQ, Prometheus e Jaeger"
	@echo "  make migrate-up    aplica as migrations pelo Flyway"
	@echo "  make generate      regera o codigo de acesso a dados (sqlc)"
	@echo "  make sqlc-check    falha se o codigo gerado estiver desatualizado"
	@echo "  make sqlc-vet      falha se uma query for invalida contra o schema (exige o banco)"
	@echo "  make api           sobe a API (Swagger em http://127.0.0.1:8000/docs)"
	@echo "  make cli ARGS=...  executa um comando, ex.: make cli ARGS='list-examples'"
	@echo "  make streamlit     sobe a tela Streamlit"
	@echo "  make outbox-job    sobe o job que drena a outbox"
	@echo "  make test-unit     testes que rodam sem Docker"
	@echo "  make check         todos os portoes"

install:
	uv sync

# ---------------------------------------------------------------------------------------------
# Stack local e schema. `migrations/` é a fonte da verdade do schema.
# ---------------------------------------------------------------------------------------------

stack-up:
	$(COMPOSE) up -d postgres rabbitmq prometheus jaeger

stack-down:
	$(COMPOSE) down

# `run --rm`, e não `up`: o Flyway é um job que roda uma vez e sai.
migrate-up:
	$(COMPOSE) run --rm flyway migrate

migrate-info:
	$(COMPOSE) run --rm flyway info

# ---------------------------------------------------------------------------------------------
# Geração com sqlc. O código gerado é COMMITADO e NUNCA editado à mão.
# ---------------------------------------------------------------------------------------------

define assert_sqlc_version
	installed=$$(sqlc version | tr -d 'v'); \
	if [[ "$$installed" != "$(SQLC_VERSION)" ]]; then \
	  echo "sqlc $$installed instalado, mas o Makefile fixa $(SQLC_VERSION)."; \
	  exit 1; \
	fi
endef

# O sqlc-gen-python não suporta `:copyfrom` nem `:batch*`. O portão aponta o arquivo e a linha.
define assert_no_unsupported_annotations
	if grep -rInE "^-- name:.*:(copyfrom|batchexec|batchmany|batchone)" queries --include=*.sql; then \
	  echo "FALHA: anotacao que o sqlc-gen-python nao gera."; \
	  exit 1; \
	fi
endef

generate:
	@$(assert_sqlc_version)
	@SQLC_DATABASE_URI="$(SQLC_DATABASE_URI)" sqlc generate
	@echo "codigo regerado: commite as pastas sqlc/ junto com o SQL que mudou"

sqlc-check:
	@$(assert_sqlc_version)
	@if ! SQLC_DATABASE_URI="$(SQLC_DATABASE_URI)" sqlc diff; then \
	  echo "FALHA: o codigo gerado esta desatualizado em relacao a migrations/ ou queries/."; \
	  echo "Rode: make generate"; \
	  exit 1; \
	fi
	@$(assert_no_unsupported_annotations)
	@echo "codigo gerado em dia"

# `sqlc/db-prepare` PREPARA cada query contra o Postgres real. Exige `stack-up` e `migrate-up`.
sqlc-vet:
	@SQLC_DATABASE_URI="$(SQLC_DATABASE_URI)" sqlc vet
	@echo "queries validas contra o schema"

# ---------------------------------------------------------------------------------------------
# Processos. Cada um lê o `.env` (copie de `.env.example`).
# ---------------------------------------------------------------------------------------------

api:
	uv run --env-file .env python entrypoint/api.py

cli:
	uv run --env-file .env python entrypoint/cli.py $(ARGS)

streamlit:
	uv run --env-file .env streamlit run entrypoint/streamlit_app.py

outbox-job:
	uv run --env-file .env python entrypoint/outbox_job.py

# ---------------------------------------------------------------------------------------------
# Portões
# ---------------------------------------------------------------------------------------------

typecheck:
	uv run mypy

test-unit:
	uv run pytest -m "not integration"

# Inclui os testes de integração, que sobem Postgres e RabbitMQ em container: exige Docker.
test:
	uv run pytest

check: typecheck sqlc-check sqlc-vet test

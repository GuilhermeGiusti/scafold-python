-- Consultas da outbox: a única entrada de SQL do gravador e do repositório da fila.
--
-- O relógio da outbox vive aqui, no banco (exceção da ADR-006): toda escrita preenche os instantes
-- explicitamente, com `now()`.

-- ---------------------------------------------------------------------------------------------
-- Gravação: sempre dentro da transação da Unit of Work que grava o estado.
-- ---------------------------------------------------------------------------------------------

-- `payload` é `jsonb`: o gerador o tipa como `Any`, e o gravador entrega a string JSON já
-- serializada, que é o que o codec de `jsonb` do dialeto asyncpg do SQLAlchemy espera.
-- name: InsertOutboxMessage :one
INSERT INTO outbox_message (
    destination, event_type, event_version, payload,
    aggregate_type, aggregate_id, correlation_id, trace_context, dispatcher,
    available_at, created_at, updated_at
) VALUES (
    sqlc.arg(destination), sqlc.arg(event_type), sqlc.arg(event_version), sqlc.arg(payload),
    sqlc.arg(aggregate_type), sqlc.arg(aggregate_id), sqlc.arg(correlation_id),
    sqlc.narg(trace_context), sqlc.arg(dispatcher),
    now(), now(), now()
)
RETURNING id, created_at;

-- Os dados de envio do RabbitMQ, na MESMA transação, com o valor congelado.
-- name: InsertOutboxMessageRabbitmq :exec
INSERT INTO outbox_message_rabbitmq (message_id, routing_key, created_at)
VALUES (sqlc.arg(message_id), sqlc.arg(routing_key), now());

-- ---------------------------------------------------------------------------------------------
-- Drenagem: uma transação POR MENSAGEM, lote sempre limitado.
-- ---------------------------------------------------------------------------------------------

-- `LIMIT 1`: uma mensagem por transação. `SKIP LOCKED` faz uma segunda cópia do job pular a linha
-- que a primeira já travou. `FOR UPDATE OF m` porque o lado externo de um LEFT JOIN não pode ser
-- travado.
-- name: ClaimNextPending :one
SELECT m.id, m.destination, m.event_type, m.event_version, m.payload,
       m.aggregate_type, m.aggregate_id, m.correlation_id, m.trace_context,
       m.dispatcher, m.attempts,
       r.routing_key
FROM outbox_message m
LEFT JOIN outbox_message_rabbitmq r ON r.message_id = m.id
WHERE m.status = 'PENDING'
  AND m.dispatcher = sqlc.arg(dispatcher)
  AND m.available_at <= now()
ORDER BY m.attempts, m.created_at
LIMIT 1
FOR UPDATE OF m SKIP LOCKED;

-- name: MarkPublished :exec
UPDATE outbox_message
SET status = 'PUBLISHED', published_at = now(), updated_at = now()
WHERE id = sqlc.arg(id);

-- O cast `::double precision` tipa o parâmetro como `float` no querier gerado.
-- name: ScheduleRetry :exec
UPDATE outbox_message
SET attempts = attempts + 1,
    available_at = now() + make_interval(secs => sqlc.arg(countdown_seconds)::double precision),
    updated_at = now()
WHERE id = sqlc.arg(id);

-- name: MarkDead :exec
UPDATE outbox_message
SET status = 'DEAD', attempts = attempts + 1, updated_at = now()
WHERE id = sqlc.arg(id);

-- name: InsertOutboxError :exec
INSERT INTO outbox_error (message_id, attempt_no, failed_at, error_kind, error_detail)
VALUES (sqlc.arg(message_id), sqlc.arg(attempt_no), now(), sqlc.arg(error_kind), sqlc.arg(error_detail));

-- ---------------------------------------------------------------------------------------------
-- Backlog: SEM filtro de carimbo, de propósito. Fora de transação.
-- ---------------------------------------------------------------------------------------------

-- name: CountPendingByDispatcher :many
SELECT dispatcher,
       count(*) AS pending,
       coalesce(extract(epoch FROM now() - min(created_at)), 0)::float8 AS oldest_age_seconds
FROM outbox_message
WHERE status = 'PENDING'
GROUP BY dispatcher;

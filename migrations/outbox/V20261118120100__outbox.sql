-- A outbox de eventos de integração (ADR-006), com o que o dispatcher `rabbitmq` usa.
--
-- O evento é gravado na MESMA transação que grava o estado e drenado depois pelo job. Habilitar
-- outro broker exige migration nova, com o carimbo no `CHECK` e a tabela de dados de envio dele.
--
-- O relógio da outbox é o do banco (exceção registrada na ADR-006): as consultas preenchem cada
-- instante com `now()`, explicitamente. O schema não tem `DEFAULT` de instante nem trigger.

CREATE TABLE outbox_message (
    id                uuid         NOT NULL DEFAULT gen_random_uuid(),
    destination       varchar(255) NOT NULL,
    event_type        varchar(128) NOT NULL,
    event_version     smallint     NOT NULL,
    payload           jsonb        NOT NULL,
    aggregate_type    varchar(64)  NOT NULL,
    aggregate_id      varchar(64)  NOT NULL,
    correlation_id    varchar(64)  NOT NULL,
    trace_context     varchar(128),
    dispatcher        varchar(16)  NOT NULL,
    status            varchar(16)  NOT NULL DEFAULT 'PENDING',
    attempts          smallint     NOT NULL DEFAULT 0,
    available_at      timestamptz  NOT NULL,
    created_at        timestamptz  NOT NULL,
    updated_at        timestamptz  NOT NULL,
    published_at      timestamptz,

    CONSTRAINT pk_outbox_message             PRIMARY KEY (id),
    CONSTRAINT ck_outbox_message_status      CHECK (status IN ('PENDING', 'PUBLISHED', 'DEAD')),
    CONSTRAINT ck_outbox_message_dispatcher  CHECK (dispatcher IN ('rabbitmq'))
);

COMMENT ON COLUMN outbox_message.id             IS 'O message_id publicado: a chave de idempotência do consumidor';
COMMENT ON COLUMN outbox_message.destination    IS 'Destino lógico; a Strategy o traduz para o alvo real';
COMMENT ON COLUMN outbox_message.correlation_id IS 'O id do trace do produtor';
COMMENT ON COLUMN outbox_message.trace_context  IS 'traceparent W3C do produtor, para o envio continuar o trace';
COMMENT ON COLUMN outbox_message.dispatcher     IS 'Carimbado na GRAVAÇÃO; a linha nunca sai por outro dispatcher';
COMMENT ON COLUMN outbox_message.attempts       IS 'Falhas de envio registradas; no máximo 5';

-- A drenagem só lê pendentes, na ordem de tentativas e criação. O índice parcial não cresce com as
-- mensagens já publicadas ou mortas.
CREATE INDEX ix_outbox_message_drain
    ON outbox_message (dispatcher, attempts, created_at)
    WHERE status = 'PENDING';

CREATE TABLE outbox_error (
    message_id    uuid         NOT NULL,
    attempt_no    smallint     NOT NULL,
    failed_at     timestamptz  NOT NULL,
    error_kind    varchar(16)  NOT NULL,
    error_detail  text         NOT NULL,

    CONSTRAINT pk_outbox_error             PRIMARY KEY (message_id, attempt_no),
    CONSTRAINT fk_outbox_error_message_id  FOREIGN KEY (message_id) REFERENCES outbox_message (id) ON DELETE CASCADE,
    CONSTRAINT ck_outbox_error_error_kind  CHECK (error_kind IN ('TRANSIENTE', 'PERMANENTE')),
    CONSTRAINT ck_outbox_error_attempt_no  CHECK (attempt_no > 0)
);

COMMENT ON COLUMN outbox_error.error_detail IS 'Código e mensagem do broker, até 500 caracteres; NUNCA o payload';

CREATE TABLE outbox_message_rabbitmq (
    message_id   uuid          NOT NULL,
    routing_key  varchar(255)  NOT NULL,
    created_at   timestamptz   NOT NULL,

    CONSTRAINT pk_outbox_message_rabbitmq             PRIMARY KEY (message_id),
    CONSTRAINT fk_outbox_message_rabbitmq_message_id  FOREIGN KEY (message_id) REFERENCES outbox_message (id) ON DELETE CASCADE
);

COMMENT ON COLUMN outbox_message_rabbitmq.routing_key IS 'Congelada na gravação; por padrão, o tipo do evento';

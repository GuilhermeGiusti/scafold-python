-- O agregado Example e suas entidades filhas: duas tabelas gravadas na mesma transação.
--
-- O schema só RECUSA: restrição, chave estrangeira e CHECK. Nenhuma trigger, function ou rule, e
-- nenhum DEFAULT de instante: o `created_at` vem do relógio injetado no use case.
--
-- Toda restrição tem nome: `pk_`, `fk_`, `uq_` ou `ck_` + `<tabela>_<coluna(s)>`. Os nomes são
-- contrato com o código: o repositório traduz a violação de `uq_example_label` em `LabelTaken`
-- pelo NOME, nunca pela mensagem do driver.
--
-- A categoria é gravada como um código de uma letra. Esse código é detalhe de armazenamento: só o
-- `ExampleRowMapper` o conhece, e o domínio segue falando `Category`.

CREATE TABLE example (
    id             uuid          NOT NULL,
    label          varchar(64)   NOT NULL,
    category_code  char(1)       NOT NULL,
    created_at     timestamptz   NOT NULL,
    archived_at    timestamptz,

    CONSTRAINT pk_example                PRIMARY KEY (id),
    CONSTRAINT uq_example_label          UNIQUE (label),
    CONSTRAINT ck_example_label          CHECK (length(label) >= 1),
    CONSTRAINT ck_example_category_code  CHECK (category_code IN ('S', 'P'))
);

CREATE TABLE example_item (
    id          uuid          NOT NULL,
    example_id  uuid          NOT NULL,
    name        varchar(64)   NOT NULL,
    position    integer       NOT NULL,

    CONSTRAINT pk_example_item                      PRIMARY KEY (id),
    CONSTRAINT fk_example_item_example_id           FOREIGN KEY (example_id) REFERENCES example (id) ON DELETE CASCADE,
    CONSTRAINT uq_example_item_example_id_position  UNIQUE (example_id, position),
    CONSTRAINT uq_example_item_example_id_name      UNIQUE (example_id, name)
);

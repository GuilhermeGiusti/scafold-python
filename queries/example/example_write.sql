-- Escrita do agregado Example. Toda query aqui roda dentro de uma Unit of Work: quem abre a
-- transação é o use case, e o repositório só pede a conexão por `write_querier`.

-- name: InsertExample :exec
INSERT INTO example (id, label, category_code, created_at, archived_at)
VALUES (sqlc.arg(id), sqlc.arg(label), sqlc.arg(category_code), sqlc.arg(created_at), sqlc.narg(archived_at));

-- name: InsertExampleItem :exec
INSERT INTO example_item (id, example_id, name, position)
VALUES (sqlc.arg(id), sqlc.arg(example_id), sqlc.arg(name), sqlc.arg(position));

-- name: UpdateExampleArchivedAt :exec
UPDATE example
SET archived_at = sqlc.narg(archived_at)
WHERE id = sqlc.arg(id);

-- Os itens saem junto, pela chave estrangeira `ON DELETE CASCADE`.
-- name: DeleteArchivedExamples :execrows
DELETE FROM example
WHERE archived_at IS NOT NULL;

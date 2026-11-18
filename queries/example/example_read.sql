-- Leitura do agregado Example. Roda dentro ou fora de uma Unit of Work, pelo `querier`.

-- name: GetExample :one
SELECT id, label, category_code, created_at, archived_at
FROM example
WHERE id = sqlc.arg(id);

-- name: ListExampleItems :many
SELECT id, example_id, name, position
FROM example_item
WHERE example_id = sqlc.arg(example_id)
ORDER BY position;

-- Leitura dedicada: devolve um resumo pronto para a tela, sem reconstruir o agregado. A query faz
-- o trabalho que o agregado faria em memória (contar os itens).
-- name: ListExampleSummaries :many
SELECT e.id, e.label, e.archived_at, count(i.id) AS item_count
FROM example e
LEFT JOIN example_item i ON i.example_id = e.id
GROUP BY e.id, e.label, e.archived_at
ORDER BY e.label
LIMIT sqlc.arg(row_limit);

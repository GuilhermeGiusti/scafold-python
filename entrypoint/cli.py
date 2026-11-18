"""Ponto de entrada da linha de comando: executa um use case a partir do shell.

    uv run --env-file .env python entrypoint/cli.py --help
    uv run --env-file .env python entrypoint/cli.py create-example --label "Relatorio" --item Capa
    uv run --env-file .env python entrypoint/cli.py list-examples --limit 10
    uv run --env-file .env python entrypoint/cli.py archive-example --id <uuid>
    uv run --env-file .env python entrypoint/cli.py purge-archived-examples

O resultado sai em JSON na saída padrão. Códigos de saída: 0 sucesso, 1 configuração recusada ou
defeito, 2 argumento inválido, 3 pedido recusado por uma regra (o JSON do erro sai na saída de erro).
"""

import os
import sys

from scafold.bootstrap.cli import run


def main() -> None:
    """O único ponto que toca ``os.environ`` e ``sys.argv``."""
    sys.exit(run(sys.argv[1:], os.environ, stdout=sys.stdout, stderr=sys.stderr))


if __name__ == "__main__":
    main()

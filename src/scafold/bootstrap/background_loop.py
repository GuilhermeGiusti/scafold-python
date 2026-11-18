"""Um event loop numa thread própria, para uma borda síncrona chamar use cases assíncronos.

O Streamlit reexecuta o script a cada interação, em threads que ele mesmo escolhe. O pool do banco
fica preso ao event loop que abriu as conexões, então todo use case do processo precisa rodar no
mesmo loop. Este loop vive o processo inteiro, e cada chamada espera o resultado.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Coroutine
from typing import Any


class BackgroundLoop:
    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._loop.run_forever, name="scafold-background-loop", daemon=True
        )
        self._thread.start()

    def run[T](self, coroutine: Coroutine[Any, Any, T], /) -> T:
        """Executa a corrotina no loop de fundo e devolve o resultado, ou levanta o erro dela."""
        return asyncio.run_coroutine_threadsafe(coroutine, self._loop).result()

    def close(self) -> None:
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join()
        self._loop.close()

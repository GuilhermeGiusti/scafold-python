"""Ponto de entrada do app Streamlit: a tela que cria, lista e arquiva Examples.

    uv run --env-file .env streamlit run entrypoint/streamlit_app.py

O Streamlit reexecuta este script a cada interação. O processo (configuração, log, telemetria,
fundação e o event loop de fundo) é montado uma vez e guardado em ``st.cache_resource``; a página é
montada a cada execução e chama os mesmos use cases da API.
"""

import os

import streamlit as st

from scafold.bootstrap.settings import ConfigurationError
from scafold.bootstrap.streamlit_app import (
    StreamlitProcess,
    build_example_page,
    build_streamlit_process,
)


@st.cache_resource
def _process() -> StreamlitProcess:
    """O único ponto que toca ``os.environ``, e só para entregá-lo à configuração."""
    return build_streamlit_process(os.environ)


def main() -> None:
    try:
        process = _process()
    except ConfigurationError as refusal:
        # A configuração recusada aparece na tela, com o nome da variável e nunca o valor.
        st.error(str(refusal))
        st.stop()
    build_example_page(process.foundation.use_cases, process.loop.run).render()


main()

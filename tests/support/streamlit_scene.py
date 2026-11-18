"""A tela Streamlit sobre os fakes, para o ``AppTest``.

O ``AppTest`` reexecuta o script a cada interação, como o Streamlit faz. A cena fica em
``st.session_state``, que vive o teste inteiro e não vaza para o próximo. Os use cases rodam com
``asyncio.run``: sobre os fakes não há pool preso a um event loop.
"""

from __future__ import annotations

import asyncio

import streamlit as st

from scafold.bootstrap.streamlit_app import build_example_page

from .scene import Scene, build_scene

_SCENE_KEY = "scene"


def render_over_fakes() -> None:
    if _SCENE_KEY not in st.session_state:
        st.session_state[_SCENE_KEY] = build_scene()
    scene: Scene = st.session_state[_SCENE_KEY]
    build_example_page(scene.use_cases, asyncio.run).render()

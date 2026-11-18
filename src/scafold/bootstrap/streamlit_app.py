"""A borda Streamlit: a montagem do processo e da página.

O Streamlit reexecuta o script a cada interação. O que vive o processo inteiro (configuração, log,
telemetria, fundação e o event loop de fundo) é montado uma vez por ``build_streamlit_process``, e o
ponto de entrada o guarda em ``st.cache_resource``. A página é montada a cada execução, barata.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from scafold.bootstrap.background_loop import BackgroundLoop
from scafold.bootstrap.composition import Foundation, UseCases, build_foundation
from scafold.bootstrap.settings import Settings
from scafold.bootstrap.telemetry import build_telemetry
from scafold.infrastructure.observability.json_log_formatter import configure_logging
from scafold.infrastructure.streamlit.example_page import ExamplePage, Runner
from scafold.infrastructure.streamlit.mappers.example_form_mapper import ExampleFormMapper
from scafold.infrastructure.streamlit.presenters.example_page_presenter import (
    ExamplePagePresenter,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class StreamlitProcess:
    foundation: Foundation
    loop: BackgroundLoop


def build_streamlit_process(environment: Mapping[str, str]) -> StreamlitProcess:
    """Uma vez por processo. Levanta ``ConfigurationError`` com a configuração recusada."""
    settings = Settings.from_environment(environment)
    configure_logging(service=settings.service_name, level=settings.log_level)
    telemetry = build_telemetry(settings)
    return StreamlitProcess(
        foundation=build_foundation(settings=settings, telemetry=telemetry), loop=BackgroundLoop()
    )


def build_example_page(use_cases: UseCases, run: Runner) -> ExamplePage:
    return ExamplePage(
        create=use_cases.create_example,
        archive=use_cases.archive_example,
        list_all=use_cases.list_examples,
        run=run,
        mapper=ExampleFormMapper(),
        presenter=ExamplePagePresenter(),
    )

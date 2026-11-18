"""Métrica de erro de tradução escrita no log."""

from __future__ import annotations

import logging


class LoggingTranslationErrorMetrics:
    """Implementa ``ITranslationErrorMetrics`` escrevendo a medição no log, em DEBUG."""

    def __init__(self, logger: logging.Logger) -> None:
        self._log = logger

    def translation_failed(self, *, gateway: str) -> None:
        self._log.debug("external_translation_errors_total{gateway=%s} +1", gateway)

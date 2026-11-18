"""Identificador do agregado Example."""

from __future__ import annotations

from typing import NewType
from uuid import UUID

ExampleId = NewType("ExampleId", UUID)

"""Identificador da entidade filha ExampleItem."""

from __future__ import annotations

from typing import NewType
from uuid import UUID

ExampleItemId = NewType("ExampleItemId", UUID)

"""Adapter interface for beancount implementations.

Each implementation provides a way to parse a .beancount string and return
structured output. Implementations are invoked as external processes (black-box).
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass
class Directive:
    """A parsed beancount directive in implementation-neutral form."""

    type: str  # "open", "close", "transaction", "balance", "pad", etc.
    date: str  # ISO 8601 date string
    meta: dict = field(default_factory=dict)
    data: dict = field(default_factory=dict)  # type-specific fields


@dataclass
class ParseResult:
    """Result of parsing a beancount string."""

    directives: list[Directive]
    errors: list[str]
    options: dict = field(default_factory=dict)


class Implementation(Protocol):
    """Protocol for a beancount implementation adapter."""

    @property
    def name(self) -> str: ...

    def parse_string(self, source: str) -> ParseResult:
        """Parse a beancount source string and return structured output."""
        ...

    def check_file(self, path: Path) -> ParseResult:
        """Parse a beancount file and return structured output."""
        ...

    def is_available(self) -> bool:
        """Check if this implementation is installed and runnable."""
        ...

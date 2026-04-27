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


@dataclass
class ColumnInfo:
    """A single column in a BQL query result."""

    name: str
    datatype: str  # "str", "int", "Decimal", "date", "Amount", "Inventory", "Position", …


@dataclass
class QueryResult:
    """Result of executing a BQL query."""

    columns: list[ColumnInfo]
    rows: list[list]
    errors: list[str] = field(default_factory=list)


CAP_PARSE = "parse"
CAP_BOOKING = "booking"
CAP_PLUGINS = "plugins"
CAP_BQL = "bql"
CAP_INCLUDES = "includes"
# Can re-serialize parsed directives back to beancount source.
CAP_PRINT = "print"
# Exposes a Python-level view of parse output that satisfies fava.beans.abc
# protocols. For a non-Python implementation this means shipping a thin
# Python frontend (e.g. a bindings module that wraps native output into
# beancount-namedtuple-compatible objects).
CAP_FAVA = "fava"
# Returns a stable hash per directive via compare.hash_entry (exclude_meta=True).
# Used by Fava's edit-flow JSON API to identify entries across reload cycles.
CAP_HASH = "hash"


class Implementation(Protocol):
    """Protocol for a beancount implementation adapter."""

    @property
    def name(self) -> str: ...

    @property
    def capabilities(self) -> set[str]: ...

    def parse_string(self, source: str) -> ParseResult:
        """Parse a beancount source string and return structured output."""
        ...

    def check_file(self, path: Path) -> ParseResult:
        """Parse a beancount file and return structured output."""
        ...

    def is_available(self) -> bool:
        """Check if this implementation is installed and runnable."""
        ...

    def execute_query(self, source: str, query: str) -> QueryResult:
        """Execute a BQL query against a beancount source string."""
        ...

    def format_source(self, source: str) -> str:
        """Parse beancount source and re-serialize it. Requires CAP_PRINT."""
        ...

    def hash_entries(self, source: str) -> list[str]:
        """Return a stable hash for each directive in source. Requires CAP_HASH.

        Hashes are computed with exclude_meta=True so they are stable across
        different file paths and line numbers. Order matches parse output.
        """
        ...

    def load_as_fava(self, source: str) -> tuple[list, list, dict]:
        """Return (entries, errors, options) as Python objects satisfying
        fava.beans.abc protocols. Requires CAP_FAVA.

        Unlike parse_string (which is JSON-oriented and subprocess-based),
        this returns live Python objects and is allowed to run in-process.
        """
        ...

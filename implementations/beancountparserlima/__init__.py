"""Adapter for beancount-parser-lima (Rust zero-copy parser)."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from implementations.adapter import (
    CAP_PARSE,
    Directive,
    Implementation,
    ParseResult,
    QueryResult,
)

# Path to the built Rust binary
_BINARY = Path(__file__).parent / "target" / "release" / "lima-parse-helper"
_BINARY_DEBUG = Path(__file__).parent / "target" / "debug" / "lima-parse-helper"


def _binary_path() -> Path | None:
    """Find the lima-parse-helper binary (prefer release, fall back to debug)."""
    if _BINARY.exists():
        return _BINARY
    if _BINARY_DEBUG.exists():
        return _BINARY_DEBUG
    return None


class BeancountParserLimaAdapter:
    """Black-box adapter for beancount-parser-lima.

    Rust-based zero-copy parser. Parser-only — no booking, interpolation,
    plugins, or BQL. Invokes a Rust binary helper via subprocess.
    """

    @property
    def name(self) -> str:
        return "beancount-parser-lima"

    @property
    def capabilities(self) -> set[str]:
        return {CAP_PARSE}

    def is_available(self) -> bool:
        binary = _binary_path()
        if binary is None:
            return False
        try:
            result = subprocess.run(
                [str(binary), "/dev/null"],
                capture_output=True,
                timeout=10,
            )
            # Will parse empty file successfully or fail gracefully
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def parse_string(self, source: str) -> ParseResult:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".beancount", delete=False
        ) as f:
            f.write(source)
            f.flush()
            return self.check_file(Path(f.name))

    def check_file(self, path: Path) -> ParseResult:
        binary = _binary_path()
        if binary is None:
            return ParseResult(
                directives=[],
                errors=["lima-parse-helper binary not found; run 'cargo build --release' in implementations/beancountparserlima/"],
            )

        result = subprocess.run(
            [str(binary), str(path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return ParseResult(
                directives=[],
                errors=[f"lima-parse-helper exited with code {result.returncode}: {result.stderr}"],
            )

        import json

        data = json.loads(result.stdout)
        directives = [
            Directive(
                type=d["type"],
                date=d["date"],
                meta=d.get("meta", {}),
                data=d.get("data", {}),
            )
            for d in data["directives"]
        ]
        return ParseResult(
            directives=directives,
            errors=data.get("errors", []),
            options=data.get("options", {}),
        )

    def execute_query(self, source: str, query: str) -> QueryResult:
        return QueryResult(
            columns=[],
            rows=[],
            errors=["BQL not supported by beancount-parser-lima"],
        )

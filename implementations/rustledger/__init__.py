"""Adapter for rustledger (Rust beancount implementation).

rustledger is a Rust re-implementation of beancount that includes its own
format spec under spec/. It's a second Rust implementation alongside limabean,
useful for cross-Rust agreement signals and spec-compliance testing.

Build the helper binary before running tests:
    cd implementations/rustledger && cargo build --release
"""

from __future__ import annotations

import json
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

_BINARY = Path(__file__).parent / "target" / "release" / "rustledger-helper"
_BINARY_DEBUG = Path(__file__).parent / "target" / "debug" / "rustledger-helper"


def _binary_path() -> Path | None:
    if _BINARY.exists():
        return _BINARY
    if _BINARY_DEBUG.exists():
        return _BINARY_DEBUG
    return None


class RustledgerAdapter:
    """Black-box adapter for rustledger.

    Rust beancount implementation with its own format spec. Parse-only tier —
    no booking, plugins, or BQL. Invokes a Rust binary helper via subprocess.
    """

    @property
    def name(self) -> str:
        return "rustledger"

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
                errors=["rustledger-helper binary not found; run 'cargo build --release' in implementations/rustledger/"],
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
                errors=[f"rustledger-helper exited with code {result.returncode}: {result.stderr}"],
            )

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
            errors=["BQL not supported by rustledger adapter"],
        )

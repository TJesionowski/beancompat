"""Adapter for limabean (Rust parse + booking via limabean-booking crate)."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from implementations.adapter import (
    CAP_BOOKING,
    CAP_PARSE,
    Directive,
    Implementation,
    ParseResult,
    QueryResult,
)

_BINARY = Path(__file__).parent / "target" / "release" / "limabean-helper"
_BINARY_DEBUG = Path(__file__).parent / "target" / "debug" / "limabean-helper"


def _binary_path() -> Path | None:
    if _BINARY.exists():
        return _BINARY
    if _BINARY_DEBUG.exists():
        return _BINARY_DEBUG
    return None


class LimabeanAdapter:
    """Black-box adapter for limabean.

    limabean is a Rust booking layer built on beancount-parser-lima.
    Invokes a Rust binary helper via subprocess; emits the same portable
    JSON schema used by all beancompat adapters.

    Build: cd implementations/limabean && cargo build --release
    The binary is at target/release/limabean-helper.

    Current state: CAP_PARSE is implemented (parse path).
    CAP_BOOKING is declared and will be exercised once the booking loop is
    implemented in src/main.rs (see the TODO block at the top of that file).
    """

    @property
    def name(self) -> str:
        return "limabean"

    @property
    def capabilities(self) -> set[str]:
        return {CAP_PARSE, CAP_BOOKING}

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
                errors=["limabean-helper binary not found; run 'cargo build --release' in implementations/limabean/"],
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
                errors=[f"limabean-helper exited with code {result.returncode}: {result.stderr}"],
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
            errors=["BQL not supported by limabean"],
        )

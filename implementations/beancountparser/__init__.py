"""Adapter for beancount-parser (LaunchPlatform Lark-based parser)."""

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


class BeancountParserAdapter:
    """Black-box adapter for beancount-parser.

    Parser-only implementation — no booking, interpolation, plugins, or BQL.
    Uses a subprocess helper to maintain black-box separation.
    """

    @property
    def name(self) -> str:
        return "beancount-parser"

    @property
    def capabilities(self) -> set[str]:
        return {CAP_PARSE}

    def is_available(self) -> bool:
        try:
            result = subprocess.run(
                ["python3", "-c", "import beancount_parser"],
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
        helper = Path(__file__).parent / "_parse_helper.py"
        result = subprocess.run(
            ["python3", str(helper), str(path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return ParseResult(
                directives=[],
                errors=[f"beancount-parser exited with code {result.returncode}: {result.stderr}"],
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
            errors=["BQL not supported by beancount-parser"],
        )

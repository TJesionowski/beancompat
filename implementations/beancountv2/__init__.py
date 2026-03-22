"""Adapter for beancount v2 (2.3.x)."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from implementations.adapter import (
    CAP_BOOKING,
    CAP_BQL,
    CAP_INCLUDES,
    CAP_PARSE,
    CAP_PLUGINS,
    Directive,
    Implementation,
    ParseResult,
    QueryResult,
)

# Use the v2 venv's Python, set via BEANCOUNT_V2_VENV env var or default path.
_DEFAULT_V2_VENV = Path(__file__).parent.parent.parent / ".venv-beancount-v2"


def _v2_python() -> str:
    venv = os.environ.get("BEANCOUNT_V2_VENV", str(_DEFAULT_V2_VENV))
    return str(Path(venv) / "bin" / "python3")


class BeancountV2Adapter:
    """Black-box adapter for beancount v2 (2.3.x).

    Uses a separate virtualenv with beancount v2 installed.
    Full capabilities: parse, booking, plugins, BQL, includes.
    """

    @property
    def name(self) -> str:
        return "beancount-v2"

    @property
    def capabilities(self) -> set[str]:
        return {CAP_PARSE, CAP_BOOKING, CAP_PLUGINS, CAP_BQL, CAP_INCLUDES}

    def is_available(self) -> bool:
        python = _v2_python()
        try:
            result = subprocess.run(
                [python, "-c", "import beancount; assert beancount.__version__.startswith('2.')"],
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
            [_v2_python(), str(helper), str(path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return ParseResult(
                directives=[],
                errors=[f"beancount-v2 exited with code {result.returncode}: {result.stderr}"],
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
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".beancount", delete=False
        ) as f:
            f.write(source)
            f.flush()
            helper = Path(__file__).parent / "_parse_helper.py"
            result = subprocess.run(
                [_v2_python(), str(helper), f.name, "--query", query],
                capture_output=True,
                text=True,
                timeout=30,
            )

        if result.returncode != 0:
            return QueryResult(
                columns=[],
                rows=[],
                errors=[f"beancount-v2 query exited with code {result.returncode}: {result.stderr}"],
            )

        import json

        data = json.loads(result.stdout)
        return QueryResult(
            columns=data.get("columns", []),
            rows=data.get("rows", []),
            errors=data.get("errors", []),
        )

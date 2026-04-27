"""Adapter for the reference beancount implementation (v3)."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from implementations.adapter import (
    CAP_BOOKING,
    CAP_BQL,
    CAP_FAVA,
    CAP_HASH,
    CAP_INCLUDES,
    CAP_PARSE,
    CAP_PLUGINS,
    CAP_PRINT,
    ColumnInfo,
    Directive,
    Implementation,
    ParseResult,
    QueryResult,
)


class BeancountAdapter:
    """Black-box adapter for the beancount Python implementation.

    Uses bean-check CLI for file checking and the loader API via a subprocess
    for parsing. For now, we use the Python API directly since beancount v3
    doesn't have a JSON output mode — but all access goes through the public
    API only (loader.load_string / loader.load_file).
    """

    @property
    def name(self) -> str:
        return "beancount"

    @property
    def capabilities(self) -> set[str]:
        return {
            CAP_PARSE,
            CAP_BOOKING,
            CAP_PLUGINS,
            CAP_BQL,
            CAP_INCLUDES,
            CAP_PRINT,
            CAP_FAVA,
            CAP_HASH,
        }

    def is_available(self) -> bool:
        try:
            result = subprocess.run(
                ["bean-check", "--help"],
                capture_output=True,
                timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def parse_string(self, source: str) -> ParseResult:
        """Parse beancount source using a subprocess to keep it black-box."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".beancount", delete=False
        ) as f:
            f.write(source)
            f.flush()
            return self.check_file(Path(f.name))

    def check_file(self, path: Path) -> ParseResult:
        """Parse a beancount file via subprocess.

        Invokes a helper script that loads the file with beancount's public
        API and emits JSON.
        """
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
                errors=[f"beancount exited with code {result.returncode}: {result.stderr}"],
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

    def format_source(self, source: str) -> str:
        """Re-serialize parsed source through beancount v3's printer."""
        helper = Path(__file__).parent / "_parse_helper.py"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".beancount", delete=False
        ) as f:
            f.write(source)
            f.flush()
            result = subprocess.run(
                ["python3", str(helper), f.name, "--format"],
                capture_output=True,
                text=True,
                timeout=30,
            )
        if result.returncode != 0:
            raise RuntimeError(
                f"beancount format exited with code {result.returncode}: {result.stderr}"
            )
        return result.stdout

    def hash_entries(self, source: str) -> list[str]:
        """Return stable hashes (exclude_meta=True) for each directive in source."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".beancount", delete=False
        ) as f:
            f.write(source)
            f.flush()
            helper = Path(__file__).parent / "_parse_helper.py"
            result = subprocess.run(
                ["python3", str(helper), f.name, "--hash"],
                capture_output=True,
                text=True,
                timeout=30,
            )
        if result.returncode != 0:
            raise RuntimeError(
                f"beancount hash exited with code {result.returncode}: {result.stderr}"
            )
        import json

        return json.loads(result.stdout)

    def parse_string_with_plugins(self, source: str, plugins: list[str]) -> ParseResult:
        prefix = "".join(f'plugin "{p}"\n' for p in plugins)
        return self.parse_string(prefix + source)

    def load_as_fava(self, source: str) -> tuple[list, list, dict]:
        """Return live Python objects from beancount.loader.load_string.

        Intentionally in-process, not subprocess — Fava-compat is a
        Python-level protocol test, not a JSON diff.
        """
        from beancount import loader

        return loader.load_string(source)

    def execute_query(self, source: str, query: str) -> QueryResult:
        """Execute a BQL query against beancount source via subprocess."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".beancount", delete=False
        ) as f:
            f.write(source)
            f.flush()
            helper = Path(__file__).parent / "_parse_helper.py"
            result = subprocess.run(
                ["python3", str(helper), f.name, "--query", query],
                capture_output=True,
                text=True,
                timeout=30,
            )

        if result.returncode != 0:
            return QueryResult(
                columns=[],
                rows=[],
                errors=[f"beancount query exited with code {result.returncode}: {result.stderr}"],
            )

        import json

        data = json.loads(result.stdout)
        columns = [
            ColumnInfo(name=c["name"], datatype=c["datatype"])
            for c in data.get("columns", [])
        ]
        return QueryResult(
            columns=columns,
            rows=data.get("rows", []),
            errors=data.get("errors", []),
        )

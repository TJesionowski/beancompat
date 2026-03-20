"""Tests for include directives and multi-file ledgers.

Real-world ledgers are split across multiple files. Fava navigates
between files — correct include handling is essential.
"""

import tempfile
from pathlib import Path


class TestIncludes:

    def test_include_another_file(self, beancount):
        """Including another file should merge its directives."""
        with tempfile.TemporaryDirectory() as tmpdir:
            main = Path(tmpdir) / "main.beancount"
            included = Path(tmpdir) / "accounts.beancount"

            included.write_text(
                "2024-01-01 open Assets:Bank USD\n"
                "2024-01-01 open Expenses:Food USD\n"
            )
            main.write_text(f"""\
include "{included}"

2024-01-15 * "Test"
  Assets:Bank  -10.00 USD
  Expenses:Food
""")
            result = beancount.check_file(main)
            assert len(result.errors) == 0
            opens = [d for d in result.directives if d.type == "open"]
            assert any(d.data["account"] == "Assets:Bank" for d in opens)

    def test_missing_include_error(self, beancount):
        """Including a nonexistent file should produce an error."""
        source = """\
include "nonexistent.beancount"

2024-01-01 open Assets:Bank USD
"""
        result = beancount.parse_string(source)
        assert len(result.errors) > 0

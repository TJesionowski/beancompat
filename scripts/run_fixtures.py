"""Run portable fixtures against a registered adapter and report pass/fail.

Usage:
    python scripts/run_fixtures.py --adapter beancount
    python scripts/run_fixtures.py --adapter beancount-parser-lima --fixture fixtures/parse/open_single.json

Exit code is the number of failing fixtures (0 = all pass).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from implementations.adapter import CAP_BOOKING, CAP_PARSE  # noqa: E402
from scripts.fixture_format import (  # noqa: E402
    contains_parse_result,
    parse_result_to_dict,
)

FIXTURES_DIR = ROOT / "fixtures"


def required_capabilities(path: Path) -> set[str]:
    tier = path.relative_to(FIXTURES_DIR).parts[0]
    if tier == "check":
        return {CAP_PARSE, CAP_BOOKING}
    return {CAP_PARSE}


def load_adapters() -> dict:
    """Import adapters lazily so missing optional deps don't break the CLI."""
    from implementations.beancount import BeancountAdapter
    from implementations.beancountparser import BeancountParserAdapter
    from implementations.beancountparserlima import BeancountParserLimaAdapter
    from implementations.beancountv2 import BeancountV2Adapter

    return {
        "beancount": BeancountAdapter,
        "beancount-v2": BeancountV2Adapter,
        "beancount-parser": BeancountParserAdapter,
        "beancount-parser-lima": BeancountParserLimaAdapter,
    }


def run_one(fixture_path: Path, adapter) -> tuple[str, str]:
    """Return (status, detail). status is one of PASS, FAIL, XFAIL, SKIP."""
    missing = required_capabilities(fixture_path) - adapter.capabilities
    if missing:
        return "SKIP", f"lacks {sorted(missing)}"

    data = json.loads(fixture_path.read_text())
    divergence = data.get("known_divergences", {}).get(adapter.name)
    if divergence is not None:
        return "XFAIL", divergence

    result = adapter.parse_string(data["source"])
    actual = parse_result_to_dict(result)
    ok, reason = contains_parse_result(actual, data["expected"])
    return ("PASS", "") if ok else ("FAIL", reason)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", required=True, help="Adapter name (e.g. beancount, beancount-parser-lima)")
    parser.add_argument(
        "--fixture",
        action="append",
        help="Path to a single fixture JSON. Repeatable. Default: all fixtures.",
    )
    args = parser.parse_args(argv[1:])

    adapters = load_adapters()
    if args.adapter not in adapters:
        print(f"error: unknown adapter {args.adapter!r}; available: {sorted(adapters)}", file=sys.stderr)
        return 2

    adapter = adapters[args.adapter]()
    if not adapter.is_available():
        print(f"error: adapter {args.adapter!r} is not available on this system", file=sys.stderr)
        return 2

    fixtures = [Path(f) for f in args.fixture] if args.fixture else sorted(FIXTURES_DIR.rglob("*.json"))
    if not fixtures:
        print("no fixtures found", file=sys.stderr)
        return 2

    counts = {"PASS": 0, "FAIL": 0, "XFAIL": 0, "SKIP": 0}
    for fp in fixtures:
        status, detail = run_one(fp, adapter)
        counts[status] += 1
        line = f"{status:5s} {fp.relative_to(ROOT)}"
        if detail:
            line += f"  — {detail}"
        print(line)

    print(
        f"\n{counts['PASS']} passed, {counts['FAIL']} failed, "
        f"{counts['XFAIL']} xfailed (known divergence), {counts['SKIP']} skipped"
    )
    return counts["FAIL"]


if __name__ == "__main__":
    sys.exit(main(sys.argv))

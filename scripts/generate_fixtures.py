"""Regenerate the `expected` field of fixture JSON files from the reference adapter.

Usage:
    python scripts/generate_fixtures.py                    # regenerate all
    python scripts/generate_fixtures.py fixtures/parse/foo.json [...]  # regenerate specific

The generator:
  1. Loads each fixture JSON (requires name, description, source).
  2. Parses `source` with the reference adapter (beancount v3).
  3. Overwrites `expected` with the neutral-dict form of the parse result.
  4. Writes the fixture back, preserving name/description/source.

Non-beancount-v3 implementations are intentionally *not* used here — the
reference is the single source of truth for generated expected output.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Make the project root importable when invoked as a script.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from implementations.beancount import BeancountAdapter  # noqa: E402
from scripts.fixture_format import parse_result_to_dict  # noqa: E402

FIXTURES_DIR = ROOT / "fixtures"


def discover() -> list[Path]:
    """Return all fixture JSON files under fixtures/."""
    return sorted(FIXTURES_DIR.rglob("*.json"))


def regenerate(path: Path, adapter: BeancountAdapter) -> None:
    data = json.loads(path.read_text())

    for required in ("name", "description", "source"):
        if required not in data:
            raise ValueError(f"{path}: missing required field {required!r}")

    # Preserve author-supplied fields (known_divergences, requires, etc.) by
    # only overwriting `expected`.

    result = adapter.parse_string(data["source"])
    expected = parse_result_to_dict(result)

    # Drop `options` from generated expected — it's too noisy and
    # implementation-specific to assert by default. Fixture authors who want
    # to assert on options can add them back manually.
    expected.pop("options", None)

    data["expected"] = expected
    path.write_text(json.dumps(data, indent=2) + "\n")
    print(f"regenerated {path.relative_to(ROOT)}")


def main(argv: list[str]) -> int:
    adapter = BeancountAdapter()
    if not adapter.is_available():
        print("error: reference adapter (beancount v3) is not available", file=sys.stderr)
        return 1

    targets = [Path(a).resolve() for a in argv[1:]] if len(argv) > 1 else discover()
    if not targets:
        print("no fixtures found", file=sys.stderr)
        return 1

    for path in targets:
        regenerate(path, adapter)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

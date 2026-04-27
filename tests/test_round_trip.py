"""Round-trip tests: parse → format → parse must yield the same directives.

Implementations that claim CAP_PRINT must be able to serialize their parsed
output back to beancount source in a way that re-parses to an equivalent
structure. This is the property Fava relies on when writing edits back to disk.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from implementations.adapter import CAP_PARSE, CAP_PRINT
from scripts.fixture_format import contains_parse_result, parse_result_to_dict
from tests.conftest import ADAPTERS

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
FIXTURE_PATHS = sorted(FIXTURES_DIR.rglob("*.json"))


def _fixture_id(path: Path) -> str:
    return str(path.relative_to(FIXTURES_DIR))


@pytest.fixture(scope="session", params=list(ADAPTERS.keys()))
def printing_adapter(request):
    adapter = ADAPTERS[request.param]()
    if not adapter.is_available():
        pytest.skip(f"{request.param} not available")
    required = {CAP_PARSE, CAP_PRINT}
    missing = required - adapter.capabilities
    if missing:
        pytest.skip(f"{request.param} lacks capabilities: {sorted(missing)}")
    return adapter


@pytest.mark.parametrize("fixture_path", FIXTURE_PATHS, ids=_fixture_id)
def test_round_trip(printing_adapter, fixture_path):
    """Format then reparse; the result must contain the original `expected`."""
    data = json.loads(fixture_path.read_text())
    divergence = data.get("known_divergences", {}).get(printing_adapter.name)
    if divergence is not None:
        pytest.xfail(f"known divergence: {divergence}")

    original = printing_adapter.parse_string(data["source"])
    formatted = printing_adapter.format_source(data["source"])
    reparsed = printing_adapter.parse_string(formatted)

    # The re-parsed result should contain the same assertions as the original.
    # Use the fixture's `expected` as the invariant so we're asserting Fava's
    # contract, not implementation-internal noise like whitespace.
    # Options are excluded: beancount's printer only emits directives, not
    # option declarations, so options are intentionally lost in the round-trip.
    expected_for_round_trip = {k: v for k, v in data["expected"].items() if k != "options"}
    actual = parse_result_to_dict(reparsed)
    ok, reason = contains_parse_result(actual, expected_for_round_trip)
    assert ok, (
        f"round-trip failed on {data['name']!r} with {printing_adapter.name}: {reason}\n"
        f"original source:\n{data['source']}\n"
        f"formatted source:\n{formatted}\n"
        f"reparsed: {json.dumps(actual, indent=2)}"
    )

    # Sanity: original and reparsed directive counts must match.
    assert len(original.directives) == len(reparsed.directives), (
        f"directive count changed: {len(original.directives)} → {len(reparsed.directives)}\n"
        f"formatted:\n{formatted}"
    )

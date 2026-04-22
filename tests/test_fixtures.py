"""Run every portable fixture against every available adapter.

Fixtures live in two tiers under `fixtures/`:

- `fixtures/parse/` — pure syntax. Runs against any adapter with CAP_PARSE.
- `fixtures/check/` — full loader semantics (booking, interpolation, date sort).
  Requires CAP_BOOKING.

A fixture may declare `known_divergences: {adapter_name: "reason"}`. Those
adapter/fixture pairs are run as xfail — a pass triggers XPASS and the
divergence entry should be removed; a fail surfaces as XFAIL (expected).

Non-Python implementations consume the same JSON files from their own
language — see fixtures/README.md for the schema and consumption recipe.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from implementations.adapter import CAP_BOOKING, CAP_PARSE
from scripts.fixture_format import contains_parse_result, parse_result_to_dict
from tests.conftest import ADAPTERS

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

FIXTURE_PATHS = sorted(FIXTURES_DIR.rglob("*.json"))


def _fixture_id(path: Path) -> str:
    return str(path.relative_to(FIXTURES_DIR))


def _required_capabilities(path: Path) -> set[str]:
    """Return the capability set required to run a fixture based on its tier."""
    tier = path.relative_to(FIXTURES_DIR).parts[0]
    if tier == "parse":
        return {CAP_PARSE}
    if tier == "check":
        return {CAP_PARSE, CAP_BOOKING}
    return {CAP_PARSE}


@pytest.fixture(scope="session", params=list(ADAPTERS.keys()))
def fixture_adapter(request):
    adapter = ADAPTERS[request.param]()
    if not adapter.is_available():
        pytest.skip(f"{request.param} not available")
    return adapter


@pytest.mark.parametrize("fixture_path", FIXTURE_PATHS, ids=_fixture_id)
def test_fixture(fixture_adapter, fixture_path):
    """Every fixture's `expected` must be contained in the adapter's parse output."""
    required = _required_capabilities(fixture_path)
    missing = required - fixture_adapter.capabilities
    if missing:
        pytest.skip(f"{fixture_adapter.name} lacks capabilities: {sorted(missing)}")

    data = json.loads(fixture_path.read_text())
    known_divergences = data.get("known_divergences", {})
    divergence_reason = known_divergences.get(fixture_adapter.name)

    if divergence_reason is not None:
        # Unconditional xfail: some divergences (e.g. non-deterministic ordering)
        # may intermittently happen to match. We don't want test flakiness, so
        # we never assert when a divergence is documented. A maintainer who
        # thinks the divergence has been fixed can remove the entry and see a
        # real pass/fail.
        pytest.xfail(f"known divergence for {fixture_adapter.name}: {divergence_reason}")

    result = fixture_adapter.parse_string(data["source"])
    actual = parse_result_to_dict(result)
    ok, reason = contains_parse_result(actual, data["expected"])

    assert ok, (
        f"fixture {data['name']!r} failed against {fixture_adapter.name}: {reason}\n"
        f"source:\n{data['source']}\n"
        f"actual: {json.dumps(actual, indent=2)}"
    )

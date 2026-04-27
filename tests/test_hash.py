"""Hash stability tests: CAP_HASH implementations return consistent entry hashes."""

from __future__ import annotations

import pytest

from implementations.adapter import CAP_HASH
from tests.conftest import ADAPTERS

_HASH_SOURCE = """\
2024-01-01 open Assets:Checking USD
2024-01-01 open Equity:Opening USD

2024-01-02 * "balance seed"
  Assets:Checking    100.00 USD
  Equity:Opening    -100.00 USD
"""

# Pinned hashes from beancount v3 compare.hash_entry(entry, exclude_meta=True).
# These are regression guards: if beancount changes its hash algorithm, these
# break intentionally so the change is visible.
_PINNED_HASHES = [
    "ecb7ac8f1c759bc9b667eedbdfd69f62",  # open Assets:Checking
    "1b704c6c92c2a000da5dcc5a334bbd18",  # open Equity:Opening
    "4bfc3577df5bd6fb04f958be62ec408d",  # transaction "balance seed"
]


_HASH_ADAPTERS = [cls() for cls in ADAPTERS.values() if CAP_HASH in cls().capabilities]


@pytest.fixture(
    params=_HASH_ADAPTERS,
    ids=lambda a: a.name,
)
def hash_adapter(request):
    adapter = request.param
    if not adapter.is_available():
        pytest.skip(f"{adapter.name} not available")
    return adapter


def test_hash_stability(hash_adapter):
    """Same source must produce identical hashes on repeated calls."""
    assert hash_adapter.hash_entries(_HASH_SOURCE) == hash_adapter.hash_entries(_HASH_SOURCE)


def test_hash_count_matches_directives(hash_adapter):
    """Number of hashes must equal number of directives in parse output."""
    result = hash_adapter.parse_string(_HASH_SOURCE)
    hashes = hash_adapter.hash_entries(_HASH_SOURCE)
    assert len(hashes) == len(result.directives)


def test_hash_are_hex_strings(hash_adapter):
    """Each hash must be a non-empty lowercase hex string."""
    hashes = hash_adapter.hash_entries(_HASH_SOURCE)
    assert len(hashes) > 0
    for h in hashes:
        assert isinstance(h, str) and len(h) > 0
        assert all(c in "0123456789abcdef" for c in h)


def test_hash_pinned_reference():
    """Regression guard: pin beancount v3 hashes for the canonical source."""
    adapter = next(
        (a for a in _HASH_ADAPTERS if a.name == "beancount"),
        None,
    )
    if adapter is None or not adapter.is_available():
        pytest.skip("beancount reference adapter not available")
    assert adapter.hash_entries(_HASH_SOURCE) == _PINNED_HASHES

"""Fava-compat tier: adapter output must satisfy fava.beans.abc protocols.

This is a separate tier from the JSON-fixture parse tier. Its purpose is to
verify an implementation can serve Fava and similar Python-API consumers.
Implementations in non-Python languages participate in this tier by shipping
a Python frontend that wraps their native output into beancount-compatible
namedtuples.

See `fava/beans/abc.py` and `fava/beans/protocols.py` in the Fava source
for the canonical contract this test enforces.
"""

from __future__ import annotations

import pytest

fava_abc = pytest.importorskip("fava.beans.abc")

from implementations.adapter import CAP_FAVA  # noqa: E402
from tests.conftest import ADAPTERS  # noqa: E402

# One representative source per directive type Fava consumes. Kept small
# because this test is about *type conformance*, not semantics — that's
# already covered by the JSON-fixture tier.
SOURCES = {
    "open": '2024-01-01 open Assets:Bank USD\n',
    "close": '2024-01-01 open Assets:Bank USD\n2024-12-31 close Assets:Bank\n',
    "transaction": (
        '2024-01-01 open Assets:Bank USD\n'
        '2024-01-01 open Expenses:Food USD\n'
        '2024-01-15 * "Grocery" "Notes"\n'
        '  Expenses:Food  50.00 USD\n'
        '  Assets:Bank   -50.00 USD\n'
    ),
    "balance": (
        '2024-01-01 open Assets:Bank USD\n'
        '2024-01-01 open Income:Salary USD\n'
        '2024-01-15 * "Deposit"\n'
        '  Assets:Bank   100.00 USD\n'
        '  Income:Salary -100.00 USD\n'
        '2024-02-01 balance Assets:Bank  100.00 USD\n'
    ),
    "commodity": '2024-01-01 commodity USD\n',
    "price": '2024-01-15 price EUR  1.10 USD\n',
    "pad": (
        '2024-01-01 open Assets:Bank USD\n'
        '2024-01-01 open Equity:Opening USD\n'
        '2024-01-02 pad Assets:Bank Equity:Opening\n'
        '2024-01-03 balance Assets:Bank  100.00 USD\n'
    ),
    "note": '2024-01-01 open Assets:Bank USD\n2024-01-15 note Assets:Bank "A note"\n',
    "event": '2024-01-15 event "location" "Boston"\n',
}

# Required ABC classes per directive type. Every entry emitted for a given
# source must pass isinstance against the matching ABC, and against the
# top-level Directive ABC as well.
EXPECTED_ABC = {
    "open": fava_abc.Open,
    "close": fava_abc.Close,
    "transaction": fava_abc.Transaction,
    "balance": fava_abc.Balance,
    "commodity": fava_abc.Commodity,
    "price": fava_abc.Price,
    "pad": fava_abc.Pad,
    "note": fava_abc.Note,
    "event": fava_abc.Event,
}

# Required attributes Fava reads off each directive type. Keyed by ABC name.
# (Source: survey of fava/beans/abc.py field declarations.)
REQUIRED_FIELDS = {
    "Transaction": ("date", "meta", "flag", "payee", "narration", "postings", "tags", "links"),
    "Posting": ("account", "units", "cost", "price", "flag", "meta"),
    "Balance": ("date", "meta", "account", "amount", "tolerance", "diff_amount"),
    "Open": ("date", "meta", "account", "currencies", "booking"),
    "Close": ("date", "meta", "account"),
    "Commodity": ("date", "meta", "currency"),
    "Price": ("date", "meta", "currency", "amount"),
    "Pad": ("date", "meta", "account", "source_account"),
    "Note": ("date", "meta", "account", "comment"),
    "Event": ("date", "meta", "type", "description"),
}


@pytest.fixture(
    scope="session",
    params=[name for name in ADAPTERS.keys()],
)
def fava_adapter(request):
    adapter = ADAPTERS[request.param]()
    if not adapter.is_available():
        pytest.skip(f"{request.param} not available")
    if CAP_FAVA not in adapter.capabilities:
        pytest.skip(f"{request.param} lacks CAP_FAVA")
    return adapter


@pytest.mark.parametrize("directive_type,source", list(SOURCES.items()))
def test_directive_satisfies_fava_abc(fava_adapter, directive_type, source):
    """Every emitted directive matches its ABC and has all Fava-required fields."""
    entries, errors, _options = fava_adapter.load_as_fava(source)
    assert not errors, f"load_as_fava reported errors: {errors}"

    expected_abc = EXPECTED_ABC[directive_type]
    matching = [e for e in entries if isinstance(e, expected_abc)]
    assert matching, (
        f"no entry of type {expected_abc.__name__} produced for {directive_type!r} source"
    )

    for entry in matching:
        # Top-level Directive ABC.
        assert isinstance(entry, fava_abc.Directive), (
            f"{type(entry).__name__} does not register as fava.beans.abc.Directive"
        )
        # Namedtuple protocol — Fava relies on _replace / _asdict for edits.
        assert hasattr(entry, "_replace"), f"{type(entry).__name__} missing _replace"
        assert hasattr(entry, "_asdict"), f"{type(entry).__name__} missing _asdict"
        # Required field set.
        abc_name = expected_abc.__name__
        for field in REQUIRED_FIELDS[abc_name]:
            assert hasattr(entry, field), (
                f"{abc_name} missing required field {field!r}"
            )

    # Transaction postings must themselves satisfy the Posting contract.
    if directive_type == "transaction":
        txn = matching[0]
        for p in txn.postings:
            assert isinstance(p, fava_abc.Posting), (
                f"posting {p!r} does not register as fava.beans.abc.Posting"
            )
            for field in REQUIRED_FIELDS["Posting"]:
                assert hasattr(p, field), f"Posting missing required field {field!r}"

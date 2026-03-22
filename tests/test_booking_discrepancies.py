"""Property-based tests comparing booking semantics between beancount v2 and v3.

These tests generate valid ledgers and compare the full semantic output
(interpolation, balance checking, cost booking) between implementations
that support booking. Parse-only implementations are excluded.
"""

from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from strategies import accounts, currencies, dates, numbers


# --- Strategies for booking-level inputs ---

_narrations = st.from_regex(r"[A-Za-z0-9 ]{1,20}", fullmatch=True)

# Amounts that don't cause precision issues
_booking_numbers = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("9999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)

# Smaller numbers for share counts
_share_counts = st.integers(min_value=1, max_value=100)

# Per-share prices
_prices = st.decimals(
    min_value=Decimal("1.00"),
    max_value=Decimal("999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)

# Stock-like currencies
_commodities = st.sampled_from(["AAPL", "GOOG", "MSFT", "AMZN", "TSLA", "VTI", "BND"])


@st.composite
def interpolated_transactions(draw):
    """Generate a transaction with one elided posting (needs interpolation)."""
    date = draw(dates)
    narration = draw(_narrations)
    currency = draw(currencies)
    amount = draw(_booking_numbers)

    from_account = draw(accounts(roots=["Assets"]))
    to_account = draw(accounts(roots=["Expenses"]))
    if from_account == to_account:
        to_account = "Expenses:Other"

    open_date = "1990-01-01"
    return "\n".join([
        f"{open_date} open {from_account} {currency}",
        f"{open_date} open {to_account} {currency}",
        "",
        f'{date} * "{narration}"',
        f"  {to_account}  {amount} {currency}",
        f"  {from_account}",
    ]) + "\n"


@st.composite
def balance_after_transactions(draw):
    """Generate transactions followed by a correct balance assertion."""
    currency = draw(currencies)
    account = draw(accounts(roots=["Assets"]))
    equity = "Equity:Opening"

    open_date = "1990-01-01"

    # Generate 1-3 transactions
    n_txns = draw(st.integers(min_value=1, max_value=3))
    total = Decimal("0")
    txn_lines = []

    for i in range(n_txns):
        amount = draw(_booking_numbers)
        # Alternate deposits and withdrawals
        if draw(st.booleans()):
            amount = -amount
        total += amount
        date = f"2024-{(i+1):02d}-15"
        txn_lines.extend([
            f'{date} * "Txn {i}"',
            f"  {account}  {amount} {currency}",
            f"  {equity}",
            "",
        ])

    balance_date = "2024-12-31"
    lines = [
        f"{open_date} open {account} {currency}",
        f"{open_date} open {equity}",
        "",
    ] + txn_lines + [
        f"{balance_date} balance {account} {total} {currency}",
    ]
    return "\n".join(lines) + "\n"


@st.composite
def cost_basis_transactions(draw):
    """Generate buy transactions with cost basis."""
    currency = draw(currencies)
    commodity = draw(_commodities)
    shares = draw(_share_counts)
    price = draw(_prices)
    total = shares * price

    brokerage = "Assets:Brokerage"
    bank = "Assets:Bank"
    open_date = "1990-01-01"
    buy_date = draw(dates)

    return "\n".join([
        f"{open_date} open {brokerage}",
        f"{open_date} open {bank} {currency}",
        "",
        f'{buy_date} * "Buy {commodity}"',
        f"  {brokerage}  {shares} {commodity} {{{price} {currency}}}",
        f"  {bank}  -{total} {currency}",
    ]) + "\n"


@st.composite
def buy_then_sell_transactions(draw):
    """Generate a buy followed by a partial sell with gains."""
    currency = draw(currencies)
    commodity = draw(_commodities)
    buy_shares = draw(st.integers(min_value=5, max_value=50))
    buy_price = draw(_prices)
    buy_total = buy_shares * buy_price

    sell_shares = draw(st.integers(min_value=1, max_value=buy_shares))
    sell_price = draw(_prices)
    sell_total = sell_shares * sell_price

    brokerage = "Assets:Brokerage"
    bank = "Assets:Bank"
    gains = "Income:Gains"
    open_date = "1990-01-01"

    return "\n".join([
        f"{open_date} open {brokerage}",
        f"{open_date} open {bank} {currency}",
        f"{open_date} open {gains} {currency}",
        "",
        f'2024-01-15 * "Buy {commodity}"',
        f"  {brokerage}  {buy_shares} {commodity} {{{buy_price} {currency}}}",
        f"  {bank}  -{buy_total} {currency}",
        "",
        f'2024-06-15 * "Sell {commodity}"',
        f"  {brokerage}  -{sell_shares} {commodity} {{{buy_price} {currency}}} @ {sell_price} {currency}",
        f"  {bank}  {sell_total} {currency}",
        f"  {gains}",
    ]) + "\n"


@st.composite
def pad_then_balance(draw):
    """Generate a pad directive followed by a balance assertion."""
    currency = draw(currencies)
    account = draw(accounts(roots=["Assets"]))
    equity = "Equity:Opening"
    target = draw(_booking_numbers)

    open_date = "1990-01-01"

    return "\n".join([
        f"{open_date} open {account} {currency}",
        f"{open_date} open {equity} {currency}",
        "",
        f"2024-01-01 pad {account} {equity}",
        f"2024-01-31 balance {account} {target} {currency}",
    ]) + "\n"


@st.composite
def fifo_sell_transactions(draw):
    """Generate two buys at different prices, then a FIFO sell."""
    currency = draw(currencies)
    commodity = draw(_commodities)

    shares1 = draw(st.integers(min_value=5, max_value=20))
    price1 = draw(_prices)
    shares2 = draw(st.integers(min_value=5, max_value=20))
    price2 = draw(_prices)
    # Ensure different prices for interesting lot matching
    if price1 == price2:
        price2 = price2 + Decimal("1.00")

    sell_shares = draw(st.integers(min_value=1, max_value=shares1))
    sell_price = draw(_prices)
    sell_total = sell_shares * sell_price

    brokerage = "Assets:Brokerage"
    bank = "Assets:Bank"
    gains = "Income:Gains"
    open_date = "1990-01-01"

    return "\n".join([
        f'{open_date} open {brokerage} "FIFO"',
        f"{open_date} open {bank} {currency}",
        f"{open_date} open {gains} {currency}",
        "",
        f'2024-01-15 * "Buy lot 1"',
        f"  {brokerage}  {shares1} {commodity} {{{price1} {currency}}}",
        f"  {bank}",
        "",
        f'2024-02-15 * "Buy lot 2"',
        f"  {brokerage}  {shares2} {commodity} {{{price2} {currency}}}",
        f"  {bank}",
        "",
        f'2024-06-15 * "Sell FIFO"',
        f"  {brokerage}  -{sell_shares} {commodity} {{}} @ {sell_price} {currency}",
        f"  {bank}  {sell_total} {currency}",
        f"  {gains}",
    ]) + "\n"


# Keys beancount adds internally
_INTERNAL_META_KEYS = {"filename", "lineno"}


def _user_meta(meta):
    return {k: v for k, v in meta.items() if k not in _INTERNAL_META_KEYS}


def _compare_booking_results(v3_result, v2_result, source, *, compare_errors=True):
    """Compare two full booking results (v3 vs v2)."""
    if compare_errors:
        # Both should agree on whether the input is valid
        v3_has_errors = len(v3_result.errors) > 0
        v2_has_errors = len(v2_result.errors) > 0
        assert v3_has_errors == v2_has_errors, (
            f"Error agreement: beancount={'errors' if v3_has_errors else 'ok'}, "
            f"beancount-v2={'errors' if v2_has_errors else 'ok'}\n"
            f"  v3 errors: {v3_result.errors}\n"
            f"  v2 errors: {v2_result.errors}\n"
            f"Input:\n{source}"
        )

    if v3_result.errors or v2_result.errors:
        return  # Don't compare directives if there are errors

    v3_dirs = v3_result.directives
    v2_dirs = v2_result.directives

    assert len(v3_dirs) == len(v2_dirs), (
        f"Directive count: beancount={len(v3_dirs)}, beancount-v2={len(v2_dirs)}\n"
        f"  v3 types: {[d.type for d in v3_dirs]}\n"
        f"  v2 types: {[d.type for d in v2_dirs]}\n"
        f"Input:\n{source}"
    )

    for i, (d3, d2) in enumerate(zip(v3_dirs, v2_dirs)):
        assert d3.type == d2.type, (
            f"Type mismatch at {i}: beancount={d3.type}, beancount-v2={d2.type}\n"
            f"Input:\n{source}"
        )
        assert d3.date == d2.date, (
            f"Date mismatch at {i}: beancount={d3.date}, beancount-v2={d2.date}\n"
            f"Input:\n{source}"
        )

        if d3.type == "transaction":
            _compare_transaction_data(d3.data, d2.data, source, i)

        # Compare user metadata
        assert _user_meta(d3.meta) == _user_meta(d2.meta), (
            f"Metadata mismatch at {i}:\n"
            f"  beancount: {_user_meta(d3.meta)}\n"
            f"  beancount-v2: {_user_meta(d2.meta)}\n"
            f"Input:\n{source}"
        )


def _compare_transaction_data(d3, d2, source, idx):
    """Compare transaction data between v2 and v3."""
    assert d3["flag"] == d2["flag"], (
        f"Flag mismatch at txn {idx}: {d3['flag']} vs {d2['flag']}\nInput:\n{source}"
    )
    assert d3["narration"] == d2["narration"], (
        f"Narration mismatch at txn {idx}\nInput:\n{source}"
    )

    p3 = d3.get("postings", [])
    p2 = d2.get("postings", [])
    assert len(p3) == len(p2), (
        f"Posting count at txn {idx}: beancount={len(p3)}, beancount-v2={len(p2)}\n"
        f"  v3: {[p['account'] for p in p3]}\n"
        f"  v2: {[p['account'] for p in p2]}\n"
        f"Input:\n{source}"
    )

    for j, (pp3, pp2) in enumerate(zip(p3, p2)):
        assert pp3["account"] == pp2["account"], (
            f"Posting {j} account at txn {idx}: {pp3['account']} vs {pp2['account']}\n"
            f"Input:\n{source}"
        )
        assert pp3["units"] == pp2["units"], (
            f"Posting {j} units at txn {idx}:\n"
            f"  beancount: {pp3['units']}\n"
            f"  beancount-v2: {pp2['units']}\n"
            f"Input:\n{source}"
        )
        assert pp3["cost"] == pp2["cost"], (
            f"Posting {j} cost at txn {idx}:\n"
            f"  beancount: {pp3['cost']}\n"
            f"  beancount-v2: {pp2['cost']}\n"
            f"Input:\n{source}"
        )
        assert pp3["price"] == pp2["price"], (
            f"Posting {j} price at txn {idx}:\n"
            f"  beancount: {pp3['price']}\n"
            f"  beancount-v2: {pp2['price']}\n"
            f"Input:\n{source}"
        )


class TestInterpolationAgreement:
    """v2 and v3 should agree on auto-balancing / interpolation."""

    @given(source=interpolated_transactions())
    @settings(max_examples=100, deadline=None)
    def test_elided_posting_filled_same(self, beancount, beancountv2, source):
        v3 = beancount.parse_string(source)
        v2 = beancountv2.parse_string(source)
        _compare_booking_results(v3, v2, source)

    @given(source=balance_after_transactions())
    @settings(max_examples=50, deadline=None)
    def test_balance_assertion_agreement(self, beancount, beancountv2, source):
        v3 = beancount.parse_string(source)
        v2 = beancountv2.parse_string(source)
        _compare_booking_results(v3, v2, source)


class TestCostBookingAgreement:
    """v2 and v3 should agree on cost basis and lot tracking."""

    @given(source=cost_basis_transactions())
    @settings(max_examples=50, deadline=None)
    def test_cost_basis_agreement(self, beancount, beancountv2, source):
        v3 = beancount.parse_string(source)
        v2 = beancountv2.parse_string(source)
        _compare_booking_results(v3, v2, source)

    @given(source=buy_then_sell_transactions())
    @settings(max_examples=50, deadline=None)
    def test_buy_sell_gains_agreement(self, beancount, beancountv2, source):
        v3 = beancount.parse_string(source)
        v2 = beancountv2.parse_string(source)
        _compare_booking_results(v3, v2, source)


class TestPadAgreement:
    """v2 and v3 should agree on pad-generated transactions."""

    @given(source=pad_then_balance())
    @settings(max_examples=50, deadline=None)
    def test_pad_fills_same(self, beancount, beancountv2, source):
        v3 = beancount.parse_string(source)
        v2 = beancountv2.parse_string(source)
        _compare_booking_results(v3, v2, source)


class TestFIFOBookingAgreement:
    """v2 and v3 should agree on FIFO lot matching."""

    @given(source=fifo_sell_transactions())
    @settings(max_examples=50, deadline=None)
    def test_fifo_lot_match_agreement(self, beancount, beancountv2, source):
        v3 = beancount.parse_string(source)
        v2 = beancountv2.parse_string(source)
        _compare_booking_results(v3, v2, source)

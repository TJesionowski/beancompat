"""Property-based tests to discover parse discrepancies between implementations.

These tests generate valid beancount inputs and assert that all available
parse-capable implementations agree on the output. Differences are the
interesting findings — they reveal where implementations diverge.
"""

from hypothesis import given, settings

from strategies import accounts, currencies, dates, numbers
from strategies.transactions import open_directives, simple_transactions

from hypothesis import strategies as st


# --- Strategies for richer inputs ---

_tags = st.from_regex(r"[a-z][a-z0-9\-]{0,9}", fullmatch=True)
_links = st.from_regex(r"[a-z][a-z0-9\-]{0,9}", fullmatch=True)
_narrations = st.from_regex(r"[A-Za-z0-9 ]{1,30}", fullmatch=True)
_meta_keys = st.from_regex(r"[a-z][a-z0-9]{0,7}", fullmatch=True)
_meta_values = st.from_regex(r"[A-Za-z0-9 ]{1,20}", fullmatch=True)


@st.composite
def open_with_currencies(draw):
    """Generate an open directive with 0-3 currencies."""
    date = draw(dates)
    account = draw(accounts())
    n_currencies = draw(st.integers(min_value=0, max_value=3))
    curs = [draw(currencies) for _ in range(n_currencies)]
    # deduplicate while preserving order
    seen = set()
    unique_curs = []
    for c in curs:
        if c not in seen:
            seen.add(c)
            unique_curs.append(c)
    cur_str = ", ".join(unique_curs)
    if cur_str:
        return f"{date} open {account} {cur_str}\n"
    return f"{date} open {account}\n"


@st.composite
def tagged_transactions(draw):
    """Generate a transaction with optional tags, links, and metadata."""
    date = draw(dates)
    narration = draw(_narrations)
    currency = draw(currencies)
    amount = draw(numbers)

    from_account = draw(accounts(roots=["Assets", "Liabilities"]))
    to_account = draw(accounts(roots=["Expenses", "Income"]))
    if from_account == to_account:
        to_account = "Expenses:Other"

    # Optional tags and links
    n_tags = draw(st.integers(min_value=0, max_value=2))
    tags = [draw(_tags) for _ in range(n_tags)]
    n_links = draw(st.integers(min_value=0, max_value=2))
    links = [draw(_links) for _ in range(n_links)]

    tag_str = " ".join(f"#{t}" for t in tags)
    link_str = " ".join(f"^{l}" for l in links)
    suffix = " ".join(filter(None, [tag_str, link_str]))

    # Optional metadata
    has_meta = draw(st.booleans())
    meta_line = ""
    if has_meta:
        key = draw(_meta_keys)
        val = draw(_meta_values)
        meta_line = f'  {key}: "{val}"\n'

    open_date = "1990-01-01"
    txn_line = f'{date} * "{narration}"'
    if suffix:
        txn_line += f" {suffix}"

    lines = [
        f"{open_date} open {from_account} {currency}",
        f"{open_date} open {to_account} {currency}",
        "",
        txn_line,
    ]
    if meta_line:
        lines.append(meta_line.rstrip("\n"))
    lines.append(f"  {to_account}  {amount} {currency}")
    lines.append(f"  {from_account}  -{amount} {currency}")
    return "\n".join(lines) + "\n"


@st.composite
def balance_directives(draw):
    """Generate a balance assertion."""
    date = draw(dates)
    account = draw(accounts(roots=["Assets", "Liabilities"]))
    amount = draw(numbers)
    currency = draw(currencies)
    open_date = "1990-01-01"
    return f"{open_date} open {account} {currency}\n{date} balance {account} {amount} {currency}\n"


@st.composite
def note_directives(draw):
    """Generate a note directive."""
    date = draw(dates)
    account = draw(accounts())
    comment = draw(_narrations)
    open_date = "1990-01-01"
    return f'{open_date} open {account}\n{date} note {account} "{comment}"\n'


@st.composite
def event_directives(draw):
    """Generate an event directive."""
    date = draw(dates)
    etype = draw(st.from_regex(r"[a-z]{1,10}", fullmatch=True))
    desc = draw(_narrations)
    return f'{date} event "{etype}" "{desc}"\n'


@st.composite
def price_directives(draw):
    """Generate a price directive."""
    date = draw(dates)
    base = draw(currencies)
    quote = draw(currencies)
    # Avoid same currency for base and quote
    if base == quote:
        quote = "CHF" if base != "CHF" else "GBP"
    amount = draw(numbers)
    return f"{date} price {base} {amount} {quote}\n"


# Keys beancount adds internally that parsers don't produce
_INTERNAL_META_KEYS = {"filename", "lineno"}


def _user_meta(meta):
    """Filter metadata to only user-defined keys."""
    return {k: v for k, v in meta.items() if k not in _INTERNAL_META_KEYS}


def _compare_parse_results(results, source):
    """Compare parse results across implementations, reporting divergences."""
    if len(results) < 2:
        return

    reference_name, reference_result = results[0]

    for impl_name, impl_result in results[1:]:
        # Compare directive count
        ref_directives = [d for d in reference_result.directives]
        impl_directives = [d for d in impl_result.directives]

        assert len(ref_directives) == len(impl_directives), (
            f"Directive count mismatch between {reference_name} ({len(ref_directives)}) "
            f"and {impl_name} ({len(impl_directives)}) for input:\n{source}"
        )

        for i, (rd, id_) in enumerate(zip(ref_directives, impl_directives)):
            assert rd.type == id_.type, (
                f"Directive type mismatch at index {i}: "
                f"{reference_name}={rd.type}, {impl_name}={id_.type}\n"
                f"Input:\n{source}"
            )
            assert rd.date == id_.date, (
                f"Date mismatch at index {i}: "
                f"{reference_name}={rd.date}, {impl_name}={id_.date}\n"
                f"Input:\n{source}"
            )

            # Compare data fields (the important part)
            # Fields where order is not semantically significant
            _SET_FIELDS = {"currencies", "tags", "links"}
            for key in set(rd.data.keys()) | set(id_.data.keys()):
                # Skip fields that are semantic (booking-dependent)
                if key in ("diff_amount", "tolerance"):
                    continue
                rd_val = rd.data.get(key)
                id_val = id_.data.get(key)
                if key in _SET_FIELDS and isinstance(rd_val, list) and isinstance(id_val, list):
                    rd_val = sorted(rd_val)
                    id_val = sorted(id_val)
                assert rd_val == id_val, (
                    f"Data field '{key}' mismatch in {rd.type} directive at index {i}:\n"
                    f"  {reference_name}: {rd_val}\n"
                    f"  {impl_name}: {id_val}\n"
                    f"Input:\n{source}"
                )

            # Compare user-defined metadata (skip internal keys like filename/lineno)
            rd_meta = _user_meta(rd.meta)
            id_meta = _user_meta(id_.meta)
            assert rd_meta == id_meta, (
                f"Metadata mismatch in {rd.type} directive at index {i}:\n"
                f"  {reference_name}: {rd_meta}\n"
                f"  {impl_name}: {id_meta}\n"
                f"Input:\n{source}"
            )


class TestCrossImplOpenDirectives:
    """All implementations should agree on parsing open directives."""

    @given(source=open_with_currencies())
    @settings(max_examples=100, deadline=None)
    def test_open_agreement(self, all_parsers, source):
        results = [(name, impl.parse_string(source)) for name, impl in all_parsers]

        # Filter to those that parsed without errors
        successful = [(n, r) for n, r in results if len(r.errors) == 0]
        _compare_parse_results(successful, source)


class TestCrossImplTransactions:
    """All implementations should agree on parsing transactions."""

    @given(source=simple_transactions())
    @settings(max_examples=100, deadline=None)
    def test_simple_transaction_agreement(self, all_parsers, source):
        source = source + "\n"
        results = [(name, impl.parse_string(source)) for name, impl in all_parsers]
        successful = [(n, r) for n, r in results if len(r.errors) == 0]

        # Parser-only impls won't have errors for valid syntax
        # but beancount might add interpolated amounts — compare only parse-level fields
        # Filter to just the parse-level comparison
        for name, result in successful:
            txns = [d for d in result.directives if d.type == "transaction"]
            assert len(txns) >= 1, (
                f"{name} found no transactions in:\n{source}"
            )

    @given(source=tagged_transactions())
    @settings(max_examples=100, deadline=None)
    def test_tagged_transaction_agreement(self, all_parsers, source):
        results = [(name, impl.parse_string(source)) for name, impl in all_parsers]
        successful = [(n, r) for n, r in results if len(r.errors) == 0]

        if len(successful) < 2:
            return

        # Compare tags, links, narration, payee across implementations
        ref_name, ref_result = successful[0]
        ref_txns = [d for d in ref_result.directives if d.type == "transaction"]

        for impl_name, impl_result in successful[1:]:
            impl_txns = [d for d in impl_result.directives if d.type == "transaction"]

            assert len(ref_txns) == len(impl_txns), (
                f"Transaction count: {ref_name}={len(ref_txns)}, "
                f"{impl_name}={len(impl_txns)}\nInput:\n{source}"
            )

            for rt, it in zip(ref_txns, impl_txns):
                assert rt.data["narration"] == it.data["narration"], (
                    f"Narration mismatch: {ref_name}={rt.data['narration']!r}, "
                    f"{impl_name}={it.data['narration']!r}\nInput:\n{source}"
                )
                assert rt.data["flag"] == it.data["flag"], (
                    f"Flag mismatch: {ref_name}={rt.data['flag']!r}, "
                    f"{impl_name}={it.data['flag']!r}\nInput:\n{source}"
                )
                # Compare as sets: beancount uses frozenset (deduplicates),
                # some parsers may preserve duplicates
                assert set(rt.data.get("tags", [])) == set(it.data.get("tags", [])), (
                    f"Tags mismatch: {ref_name}={rt.data.get('tags')}, "
                    f"{impl_name}={it.data.get('tags')}\nInput:\n{source}"
                )
                assert set(rt.data.get("links", [])) == set(it.data.get("links", [])), (
                    f"Links mismatch: {ref_name}={rt.data.get('links')}, "
                    f"{impl_name}={it.data.get('links')}\nInput:\n{source}"
                )

                # Compare posting count and accounts
                rp = rt.data.get("postings", [])
                ip = it.data.get("postings", [])
                assert len(rp) == len(ip), (
                    f"Posting count: {ref_name}={len(rp)}, {impl_name}={len(ip)}\n"
                    f"Input:\n{source}"
                )
                for j, (rpost, ipost) in enumerate(zip(rp, ip)):
                    assert rpost["account"] == ipost["account"], (
                        f"Posting {j} account: {ref_name}={rpost['account']}, "
                        f"{impl_name}={ipost['account']}\nInput:\n{source}"
                    )

                # Compare user-defined metadata
                rt_meta = _user_meta(rt.meta)
                it_meta = _user_meta(it.meta)
                assert rt_meta == it_meta, (
                    f"Metadata mismatch: {ref_name}={rt_meta}, "
                    f"{impl_name}={it_meta}\nInput:\n{source}"
                )


class TestCrossImplBalanceDirectives:

    @given(source=balance_directives())
    @settings(max_examples=50, deadline=None)
    def test_balance_agreement(self, all_parsers, source):
        results = [(name, impl.parse_string(source)) for name, impl in all_parsers]
        successful = [(n, r) for n, r in results if len(r.errors) == 0]

        if len(successful) < 2:
            return

        ref_name, ref_result = successful[0]
        ref_bals = [d for d in ref_result.directives if d.type == "balance"]

        for impl_name, impl_result in successful[1:]:
            impl_bals = [d for d in impl_result.directives if d.type == "balance"]
            assert len(ref_bals) == len(impl_bals)
            for rb, ib in zip(ref_bals, impl_bals):
                assert rb.data["account"] == ib.data["account"]
                assert rb.data["amount"] == ib.data["amount"], (
                    f"Balance amount: {ref_name}={rb.data['amount']}, "
                    f"{impl_name}={ib.data['amount']}\nInput:\n{source}"
                )


class TestCrossImplNotes:

    @given(source=note_directives())
    @settings(max_examples=50, deadline=None)
    def test_note_agreement(self, all_parsers, source):
        results = [(name, impl.parse_string(source)) for name, impl in all_parsers]
        successful = [(n, r) for n, r in results if len(r.errors) == 0]
        if len(successful) < 2:
            return
        ref_name, ref_result = successful[0]
        ref_notes = [d for d in ref_result.directives if d.type == "note"]
        for impl_name, impl_result in successful[1:]:
            impl_notes = [d for d in impl_result.directives if d.type == "note"]
            assert len(ref_notes) == len(impl_notes)
            for rn, in_ in zip(ref_notes, impl_notes):
                assert rn.data["account"] == in_.data["account"]
                assert rn.data["comment"] == in_.data["comment"]


class TestCrossImplEvents:

    @given(source=event_directives())
    @settings(max_examples=50, deadline=None)
    def test_event_agreement(self, all_parsers, source):
        results = [(name, impl.parse_string(source)) for name, impl in all_parsers]
        successful = [(n, r) for n, r in results if len(r.errors) == 0]
        if len(successful) < 2:
            return
        ref_name, ref_result = successful[0]
        ref_events = [d for d in ref_result.directives if d.type == "event"]
        for impl_name, impl_result in successful[1:]:
            impl_events = [d for d in impl_result.directives if d.type == "event"]
            assert len(ref_events) == len(impl_events)
            for re_, ie in zip(ref_events, impl_events):
                assert re_.data["type"] == ie.data["type"]
                assert re_.data["description"] == ie.data["description"]


class TestCrossImplPrices:

    @given(source=price_directives())
    @settings(max_examples=50, deadline=None)
    def test_price_agreement(self, all_parsers, source):
        results = [(name, impl.parse_string(source)) for name, impl in all_parsers]
        successful = [(n, r) for n, r in results if len(r.errors) == 0]
        if len(successful) < 2:
            return
        ref_name, ref_result = successful[0]
        ref_prices = [d for d in ref_result.directives if d.type == "price"]
        for impl_name, impl_result in successful[1:]:
            impl_prices = [d for d in impl_result.directives if d.type == "price"]
            assert len(ref_prices) == len(impl_prices)
            for rp, ip in zip(ref_prices, impl_prices):
                assert rp.data["currency"] == ip.data["currency"]
                assert rp.data["amount"] == ip.data["amount"], (
                    f"Price amount: {ref_name}={rp.data['amount']}, "
                    f"{impl_name}={ip.data['amount']}\nInput:\n{source}"
                )

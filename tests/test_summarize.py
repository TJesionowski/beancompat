"""Tests for CAP_SUMMARIZE date-range windowing via clamp().

clamp(source, start_date, end_date) maps to beancount.ops.summarize.clamp_opt.
end_date is EXCLUSIVE (one day past the last desired date).
Entries before start_date are summarized into opening-balance transactions;
entries on or after end_date are dropped.
"""

import pytest

from implementations.adapter import CAP_SUMMARIZE

_BASE = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD
2024-01-01 open Income:Salary USD

2024-01-15 * "Salary"
  Assets:Bank        1000.00 USD
  Income:Salary     -1000.00 USD

2024-02-15 * "Groceries"
  Expenses:Food       50.00 USD
  Assets:Bank        -50.00 USD

2024-03-15 * "More groceries"
  Expenses:Food       30.00 USD
  Assets:Bank        -30.00 USD
"""


@pytest.fixture(autouse=True)
def require_summarize(beancount):
    if CAP_SUMMARIZE not in beancount.capabilities:
        pytest.skip("CAP_SUMMARIZE not supported")


class TestClamp:

    def test_entry_on_start_date_is_included(self, beancount):
        """Entry dated exactly on start_date appears in the clamped output."""
        result = beancount.clamp(_BASE, "2024-02-15", "2024-03-01")
        assert len(result.errors) == 0
        txns = [d for d in result.directives if d.type == "transaction" and d.date == "2024-02-15"]
        groceries = [t for t in txns if t.data.get("narration") == "Groceries"]
        assert len(groceries) == 1

    def test_entry_on_end_date_is_excluded(self, beancount):
        """Entry dated exactly on end_date is NOT included (end_date is exclusive)."""
        result = beancount.clamp(_BASE, "2024-02-01", "2024-03-15")
        assert len(result.errors) == 0
        txns = [d for d in result.directives if d.type == "transaction"]
        mar_txns = [t for t in txns if t.date >= "2024-03-15"]
        assert len(mar_txns) == 0

    def test_empty_window_has_opening_entries(self, beancount):
        """A window with no regular transactions still produces opening-balance entries."""
        # Start after all transactions; no regular entries should appear
        result = beancount.clamp(_BASE, "2024-04-01", "2024-05-01")
        assert len(result.errors) == 0
        txns = [d for d in result.directives if d.type == "transaction"]
        # All transactions are opening-balance summarizations
        assert len(txns) >= 1
        for t in txns:
            assert "Summarization" in t.data.get("narration", "") or "Opening" in t.data.get("narration", "")

    def test_opening_entry_narration_shape(self, beancount):
        """Opening-balance summarization entries have the expected narration pattern."""
        result = beancount.clamp(_BASE, "2024-02-01", "2024-03-01")
        assert len(result.errors) == 0
        opening_txns = [
            d for d in result.directives
            if d.type == "transaction" and "Summarization" in d.data.get("narration", "")
        ]
        assert len(opening_txns) >= 1
        for t in opening_txns:
            narration = t.data["narration"]
            assert "Opening balance" in narration

    def test_opening_entry_postings_include_equity_account(self, beancount):
        """Opening-balance entries post against an Equity account."""
        result = beancount.clamp(_BASE, "2024-02-01", "2024-03-01")
        assert len(result.errors) == 0
        opening_txns = [
            d for d in result.directives
            if d.type == "transaction" and "Summarization" in d.data.get("narration", "")
        ]
        assert len(opening_txns) >= 1
        for t in opening_txns:
            accounts = [p["account"] for p in t.data.get("postings", [])]
            has_equity = any(a.startswith("Equity:") for a in accounts)
            assert has_equity, f"No Equity posting in opening entry: {accounts}"

    def test_pre_window_transactions_excluded(self, beancount):
        """Regular transactions before start_date do not appear directly."""
        result = beancount.clamp(_BASE, "2024-02-01", "2024-03-01")
        assert len(result.errors) == 0
        jan_txns = [
            d for d in result.directives
            if d.type == "transaction"
            and d.date < "2024-01-31"  # opening balance entries are dated begin_date-1
            and "Summarization" not in d.data.get("narration", "")
        ]
        assert len(jan_txns) == 0

    def test_window_respects_end_boundary(self, beancount):
        """Only transactions strictly before end_date appear in output."""
        # Window: Feb only
        result = beancount.clamp(_BASE, "2024-02-01", "2024-03-01")
        assert len(result.errors) == 0
        regular_txns = [
            d for d in result.directives
            if d.type == "transaction" and "Summarization" not in d.data.get("narration", "")
        ]
        assert all(d.date < "2024-03-01" for d in regular_txns)

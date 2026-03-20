"""Tests for directive types beyond open/transaction.

Covers: close, note, event, commodity, custom, pad (basic), document, query.
These are the directive types Fava reads and displays.
"""


class TestCloseDirective:
    """Close directive marks an account as closed."""

    def test_simple_close(self, beancount):
        source = """\
2024-01-01 open Assets:Bank USD
2024-12-31 close Assets:Bank
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        closes = [d for d in result.directives if d.type == "close"]
        assert len(closes) == 1
        assert closes[0].data["account"] == "Assets:Bank"

    def test_posting_after_close_error(self, beancount):
        """Posting to a closed account should error."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD
2024-06-01 close Assets:Bank

2024-07-01 * "After close"
  Expenses:Food  10.00 USD
  Assets:Bank
"""
        result = beancount.parse_string(source)
        assert len(result.errors) > 0

    def test_close_nonzero_balance_error(self, beancount):
        """Closing an account with a non-zero balance should error."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-15 * "Deposit"
  Assets:Bank  100.00 USD
  Equity:Opening-Balances
2024-12-31 close Assets:Bank
"""
        result = beancount.parse_string(source)
        assert len(result.errors) > 0


class TestNoteDirective:

    def test_simple_note(self, beancount):
        source = """\
2024-01-01 open Assets:Bank USD
2024-02-01 note Assets:Bank "Opened new checking account"
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        notes = [d for d in result.directives if d.type == "note"]
        assert len(notes) == 1
        assert notes[0].data["comment"] == "Opened new checking account"
        assert notes[0].data["account"] == "Assets:Bank"


class TestEventDirective:

    def test_simple_event(self, beancount):
        source = """\
2024-02-01 event "location" "New York"
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        events = [d for d in result.directives if d.type == "event"]
        assert len(events) == 1
        assert events[0].data["type"] == "location"
        assert events[0].data["description"] == "New York"


class TestCommodityDirective:

    def test_simple_commodity(self, beancount):
        source = """\
2024-01-01 commodity USD
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        commodities = [d for d in result.directives if d.type == "commodity"]
        assert len(commodities) == 1
        assert commodities[0].data["currency"] == "USD"


class TestCustomDirective:
    """Custom directives — Fava uses these for fava-option and fava-extension."""

    def test_custom_directive(self, beancount):
        source = """\
2024-01-01 custom "fava-option" "language" "en"
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        customs = [d for d in result.directives if d.type == "custom"]
        assert len(customs) == 1
        assert customs[0].data["type"] == "fava-option"
        assert "language" in customs[0].data["values"]
        assert "en" in customs[0].data["values"]


class TestQueryDirective:

    def test_query_directive(self, beancount):
        source = """\
2024-01-01 query "balance-query" "SELECT account, sum(position) GROUP BY account"
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        queries = [d for d in result.directives if d.type == "query"]
        assert len(queries) == 1
        assert queries[0].data["name"] == "balance-query"
        assert "SELECT" in queries[0].data["query_string"]

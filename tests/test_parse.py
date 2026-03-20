"""Tests for basic parsing of beancount directives."""

from hypothesis import given, settings

from strategies import open_directives, simple_transactions


class TestOpenDirective:
    """Hand-written tests for the open directive."""

    def test_single_open(self, beancount):
        """A single open directive should parse to one directive with no errors."""
        source = "2024-01-01 open Assets:Bank USD\n"
        result = beancount.parse_string(source)

        assert len(result.errors) == 0, f"Unexpected errors: {result.errors}"
        assert len(result.directives) == 1

        d = result.directives[0]
        assert d.type == "open"
        assert d.date == "2024-01-01"
        assert d.data["account"] == "Assets:Bank"
        assert d.data["currencies"] == ["USD"]

    def test_open_multiple_currencies(self, beancount):
        """An open directive can list multiple currencies."""
        source = "2024-01-01 open Assets:Bank USD,EUR,GBP\n"
        result = beancount.parse_string(source)

        assert len(result.errors) == 0
        assert len(result.directives) == 1
        assert set(result.directives[0].data["currencies"]) == {"USD", "EUR", "GBP"}

    def test_open_no_currency(self, beancount):
        """An open directive with no currency constraint should parse."""
        source = "2024-01-01 open Expenses:Food\n"
        result = beancount.parse_string(source)

        assert len(result.errors) == 0
        assert len(result.directives) == 1
        assert result.directives[0].data["currencies"] == []


class TestSimpleTransaction:
    """Hand-written tests for simple transactions."""

    def test_balanced_transaction(self, beancount):
        """A two-posting balanced transaction should parse without errors."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD

2024-01-15 * "Grocery store" "Weekly groceries"
  Expenses:Food  50.00 USD
  Assets:Bank   -50.00 USD
"""
        result = beancount.parse_string(source)

        assert len(result.errors) == 0
        txns = [d for d in result.directives if d.type == "transaction"]
        assert len(txns) == 1
        assert txns[0].data["payee"] == "Grocery store"
        assert txns[0].data["narration"] == "Weekly groceries"
        assert len(txns[0].data["postings"]) == 2

    def test_auto_balance_posting(self, beancount):
        """A transaction with one amount elided should auto-balance."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD

2024-01-15 * "Lunch"
  Expenses:Food  12.50 USD
  Assets:Bank
"""
        result = beancount.parse_string(source)

        assert len(result.errors) == 0
        txns = [d for d in result.directives if d.type == "transaction"]
        assert len(txns) == 1
        postings = txns[0].data["postings"]
        assert len(postings) == 2


class TestGenerativeParse:
    """Generative tests: any valid generated input should parse without errors."""

    @given(source=open_directives())
    @settings(max_examples=50)
    def test_open_directive_parses(self, beancount, source):
        """Any generated open directive should parse without errors."""
        result = beancount.parse_string(source + "\n")

        assert len(result.errors) == 0, (
            f"Failed to parse generated open directive:\n{source}\nErrors: {result.errors}"
        )
        assert len(result.directives) == 1
        assert result.directives[0].type == "open"

    @given(source=simple_transactions())
    @settings(max_examples=50)
    def test_transaction_parses(self, beancount, source):
        """Any generated balanced transaction should parse without errors."""
        result = beancount.parse_string(source + "\n")

        assert len(result.errors) == 0, (
            f"Failed to parse generated transaction:\n{source}\nErrors: {result.errors}"
        )
        txns = [d for d in result.directives if d.type == "transaction"]
        assert len(txns) == 1

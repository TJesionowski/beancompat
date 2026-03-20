"""Tests for auto-balancing / interpolation behavior.

Beancount can fill in missing amounts on postings. The rules for when and
how this works are a significant part of the 0.8→1.0 surface.
"""


class TestAutoBalance:
    """Automatic filling of elided posting amounts."""

    def test_single_elided_posting(self, beancount):
        """One posting with no amount should be auto-filled to balance."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD

2024-01-15 * "Lunch"
  Expenses:Food  12.50 USD
  Assets:Bank
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0

        txn = [d for d in result.directives if d.type == "transaction"][0]
        bank = [p for p in txn.data["postings"] if p["account"] == "Assets:Bank"][0]
        assert bank["units"]["number"] == "-12.50"

    def test_two_elided_postings_error(self, beancount):
        """Two elided postings in a single currency should error."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Assets:Cash USD
2024-01-01 open Expenses:Food USD

2024-01-15 * "Ambiguous"
  Expenses:Food  12.50 USD
  Assets:Bank
  Assets:Cash
"""
        result = beancount.parse_string(source)
        assert len(result.errors) > 0

    def test_multi_currency_auto_balance(self, beancount):
        """Each currency can have one elided posting independently."""
        source = """\
2024-01-01 open Assets:Bank USD,EUR
2024-01-01 open Expenses:Food USD,EUR

2024-01-15 * "Dinner"
  Expenses:Food  50.00 USD
  Expenses:Food  30.00 EUR
  Assets:Bank   -50.00 USD
  Assets:Bank
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0

    def test_cost_auto_balance(self, beancount):
        """Auto-balance with cost should compute the cash leg."""
        source = """\
2024-01-01 open Assets:Brokerage
2024-01-01 open Assets:Bank USD

2024-01-15 * "Buy"
  Assets:Brokerage  10 AAPL {150.00 USD}
  Assets:Bank
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0

        txn = [d for d in result.directives if d.type == "transaction"][0]
        bank = [p for p in txn.data["postings"] if p["account"] == "Assets:Bank"][0]
        assert bank["units"]["number"] == "-1500.00"

    def test_unbalanced_transaction_error(self, beancount):
        """A transaction that doesn't balance should produce an error."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD

2024-01-15 * "Wrong amounts"
  Expenses:Food  50.00 USD
  Assets:Bank   -49.00 USD
"""
        result = beancount.parse_string(source)
        assert len(result.errors) > 0


class TestTolerances:
    """Tolerance behavior for balancing."""

    def test_within_tolerance(self, beancount):
        """Small rounding differences within tolerance should not error."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD

2024-01-15 * "Rounding"
  Expenses:Food  33.33 USD
  Expenses:Food  33.33 USD
  Expenses:Food  33.33 USD
  Assets:Bank   -99.99 USD
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0

    def test_outside_tolerance(self, beancount):
        """Differences beyond tolerance should error."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD

2024-01-15 * "Too far off"
  Expenses:Food  100.00 USD
  Assets:Bank    -99.00 USD
"""
        result = beancount.parse_string(source)
        assert len(result.errors) > 0

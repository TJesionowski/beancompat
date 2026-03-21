"""Tests for number formatting edge cases.

Number representation is where implementations most likely silently diverge —
precision, large values, negatives, and tolerance derivation all matter for
balance checks.
"""

from decimal import Decimal


class TestNumberFormatting:

    def test_large_numbers(self, beancount):
        """Large numbers preserved exactly."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Income:Salary USD

2024-01-15 * "Big deposit"
  Assets:Bank    1234567.89 USD
  Income:Salary -1234567.89 USD
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        txn = [d for d in result.directives if d.type == "transaction"][0]
        posting = [p for p in txn.data["postings"]
                   if p["account"] == "Assets:Bank"][0]
        assert Decimal(posting["units"]["number"]) == Decimal("1234567.89")

    def test_small_numbers(self, beancount):
        """Small numbers preserved."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Misc USD

2024-01-15 * "Tiny amount"
  Expenses:Misc   0.01 USD
  Assets:Bank    -0.01 USD
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        txn = [d for d in result.directives if d.type == "transaction"][0]
        posting = [p for p in txn.data["postings"]
                   if p["account"] == "Expenses:Misc"][0]
        assert Decimal(posting["units"]["number"]) == Decimal("0.01")

    def test_high_precision(self, beancount):
        """All decimal places preserved for high-precision numbers."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Misc USD

2024-01-15 * "Precise"
  Expenses:Misc   1.123456 USD
  Assets:Bank    -1.123456 USD
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        txn = [d for d in result.directives if d.type == "transaction"][0]
        posting = [p for p in txn.data["postings"]
                   if p["account"] == "Expenses:Misc"][0]
        assert Decimal(posting["units"]["number"]) == Decimal("1.123456")

    def test_zero_amounts(self, beancount):
        """Zero amounts stored correctly."""
        source = """\
2024-01-01 open Assets:Bank USD

2024-01-15 balance Assets:Bank 0.00 USD
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        bal = [d for d in result.directives if d.type == "balance"][0]
        assert Decimal(bal.data["amount"]["number"]) == Decimal("0.00")

    def test_negative_amounts(self, beancount):
        """Negative amounts in auto-balanced posting."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD

2024-01-15 * "Lunch"
  Expenses:Food  50.00 USD
  Assets:Bank
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        txn = [d for d in result.directives if d.type == "transaction"][0]
        bank_posting = [p for p in txn.data["postings"]
                        if p["account"] == "Assets:Bank"][0]
        assert Decimal(bank_posting["units"]["number"]) == Decimal("-50.00")

    def test_render_commas_option(self, beancount):
        """Input with commas accepted when render_commas option set."""
        source = """\
option "render_commas" "TRUE"

2024-01-01 open Assets:Bank USD
2024-01-01 open Income:Salary USD

2024-01-15 * "Salary"
  Assets:Bank     1,234.56 USD
  Income:Salary  -1,234.56 USD
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        txn = [d for d in result.directives if d.type == "transaction"][0]
        posting = [p for p in txn.data["postings"]
                   if p["account"] == "Assets:Bank"][0]
        assert Decimal(posting["units"]["number"]) == Decimal("1234.56")

    def test_tolerance_from_precision(self, beancount):
        """Numbers with different decimal places get different tolerances."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD
2024-01-01 open Expenses:Precise USD

2024-01-15 * "Two decimal places"
  Expenses:Food   33.33 USD
  Assets:Bank    -33.33 USD

2024-01-16 * "Three decimal places"
  Expenses:Precise  33.333 USD
  Assets:Bank      -33.333 USD

2024-01-17 balance Assets:Bank -66.663 USD
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0

"""Tests for transaction flags.

Beancount supports * (cleared) and ! (pending) flags.
Fava displays these differently and allows filtering by flag.
"""


class TestTransactionFlags:

    def test_cleared_flag(self, beancount):
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD

2024-01-15 * "Cleared"
  Expenses:Food  12.50 USD
  Assets:Bank
"""
        result = beancount.parse_string(source)
        txn = [d for d in result.directives if d.type == "transaction"][0]
        assert txn.data["flag"] == "*"

    def test_pending_flag(self, beancount):
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD

2024-01-15 ! "Pending"
  Expenses:Food  12.50 USD
  Assets:Bank
"""
        result = beancount.parse_string(source)
        txn = [d for d in result.directives if d.type == "transaction"][0]
        assert txn.data["flag"] == "!"

    def test_posting_flag(self, beancount):
        """Individual postings can have flags."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD

2024-01-15 * "Posting flag"
  ! Expenses:Food  12.50 USD
  Assets:Bank
"""
        result = beancount.parse_string(source)
        txn = [d for d in result.directives if d.type == "transaction"][0]
        food = [p for p in txn.data["postings"] if p["account"] == "Expenses:Food"][0]
        assert food["flag"] == "!"

    def test_payee_narration(self, beancount):
        """Payee and narration are separate fields."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD

2024-01-15 * "Restaurant" "Dinner with friends"
  Expenses:Food  50.00 USD
  Assets:Bank
"""
        result = beancount.parse_string(source)
        txn = [d for d in result.directives if d.type == "transaction"][0]
        assert txn.data["payee"] == "Restaurant"
        assert txn.data["narration"] == "Dinner with friends"

    def test_narration_only(self, beancount):
        """A single string is narration, not payee."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD

2024-01-15 * "Just narration"
  Expenses:Food  12.50 USD
  Assets:Bank
"""
        result = beancount.parse_string(source)
        txn = [d for d in result.directives if d.type == "transaction"][0]
        assert txn.data["payee"] is None
        assert txn.data["narration"] == "Just narration"

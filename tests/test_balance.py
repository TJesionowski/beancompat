"""Tests for balance assertions and pad directives."""


class TestBalanceAssertion:
    """Balance directives assert the total of an account at a given date."""

    def test_passing_balance(self, beancount):
        """A correct balance assertion should produce no errors."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Equity:Opening-Balances USD

2024-01-15 * "Deposit"
  Assets:Bank  1000.00 USD
  Equity:Opening-Balances

2024-01-31 balance Assets:Bank 1000.00 USD
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0

    def test_failing_balance(self, beancount):
        """An incorrect balance assertion should produce an error."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Equity:Opening-Balances USD

2024-01-15 * "Deposit"
  Assets:Bank  1000.00 USD
  Equity:Opening-Balances

2024-01-31 balance Assets:Bank 999.00 USD
"""
        result = beancount.parse_string(source)
        assert len(result.errors) > 0
        assert any("balance" in str(e).lower() for e in result.errors)

    def test_balance_zero_initial(self, beancount):
        """An account with no transactions should balance to zero."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-31 balance Assets:Bank 0.00 USD
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0

    def test_balance_multiple_currencies(self, beancount):
        """Balance assertions are per-currency."""
        source = """\
2024-01-01 open Assets:Bank USD,EUR
2024-01-01 open Equity:Opening-Balances

2024-01-15 * "Deposit USD"
  Assets:Bank  1000.00 USD
  Equity:Opening-Balances

2024-01-16 * "Deposit EUR"
  Assets:Bank  500.00 EUR
  Equity:Opening-Balances

2024-01-31 balance Assets:Bank 1000.00 USD
2024-01-31 balance Assets:Bank  500.00 EUR
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0

    def test_balance_tolerance(self, beancount):
        """Balance assertions have a tolerance (default 0.005 for 2 decimal places)."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Equity:Opening-Balances USD

2024-01-15 * "Deposit"
  Assets:Bank  1000.004 USD
  Equity:Opening-Balances

2024-01-31 balance Assets:Bank 1000.00 USD
"""
        result = beancount.parse_string(source)
        # Within default tolerance of 0.005
        assert len(result.errors) == 0


class TestPadDirective:
    """Pad directives automatically insert transactions to satisfy balance assertions."""

    def test_simple_pad(self, beancount):
        """A pad should insert a transaction to satisfy the following balance."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Equity:Opening-Balances USD

2024-01-01 pad Assets:Bank Equity:Opening-Balances
2024-01-31 balance Assets:Bank 1000.00 USD
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0

        # The pad should generate a transaction
        txns = [d for d in result.directives if d.type == "transaction"]
        assert len(txns) == 1
        assert txns[0].data["flag"] == "P"  # pad flag

    def test_pad_adjusts_to_balance(self, beancount):
        """Pad + existing transactions should combine to match the balance."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Equity:Opening-Balances USD
2024-01-01 open Expenses:Food USD

2024-01-01 pad Assets:Bank Equity:Opening-Balances

2024-01-15 * "Withdrawal"
  Assets:Bank  -200.00 USD
  Expenses:Food

2024-01-31 balance Assets:Bank 800.00 USD
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0

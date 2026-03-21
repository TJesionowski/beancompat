"""Tests for multi-currency transactions and conversion semantics.

Currency conversions are a frequent source of divergence — per-unit vs total
price, auto-balancing across currencies, and cost+price interactions all
exercise different code paths.
"""

from decimal import Decimal


class TestCurrencyConversions:

    def test_per_unit_price(self, beancount):
        """Per-unit price syntax: EUR @ USD."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Assets:Foreign EUR

2024-01-15 * "Exchange"
  Assets:Foreign  100.00 EUR @ 1.10 USD
  Assets:Bank    -110.00 USD
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        txn = [d for d in result.directives if d.type == "transaction"][0]
        eur_posting = [p for p in txn.data["postings"]
                       if p["account"] == "Assets:Foreign"][0]
        assert eur_posting["price"]["number"] == "1.10"
        assert eur_posting["price"]["currency"] == "USD"

    def test_total_price(self, beancount):
        """Total price syntax: EUR @@ USD computes per-unit rate."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Assets:Foreign EUR

2024-01-15 * "Exchange"
  Assets:Foreign  100.00 EUR @@ 110.00 USD
  Assets:Bank    -110.00 USD
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        txn = [d for d in result.directives if d.type == "transaction"][0]
        eur_posting = [p for p in txn.data["postings"]
                       if p["account"] == "Assets:Foreign"][0]
        # 110 / 100 = 1.1 per unit
        assert Decimal(eur_posting["price"]["number"]) == Decimal("1.1")

    def test_implicit_conversion_residual(self, beancount):
        """Mixed currencies without price annotation — produces residual or error."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Assets:Foreign EUR

2024-01-15 * "Unpriced exchange"
  Assets:Foreign  100.00 EUR
  Assets:Bank    -110.00 USD
"""
        result = beancount.parse_string(source)
        # This should either produce an error or leave a residual
        # beancount allows this but leaves currencies unlinked
        txn = [d for d in result.directives if d.type == "transaction"]
        assert len(txn) == 1

    def test_conversion_with_auto_balance(self, beancount):
        """Elided posting in multi-currency transaction with price."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Assets:Foreign EUR

2024-01-15 * "Exchange"
  Assets:Foreign  100.00 EUR @ 1.10 USD
  Assets:Bank
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        txn = [d for d in result.directives if d.type == "transaction"][0]
        bank_posting = [p for p in txn.data["postings"]
                        if p["account"] == "Assets:Bank"][0]
        # Auto-balanced to -110.00 USD
        assert Decimal(bank_posting["units"]["number"]) == Decimal("-110.00")
        assert bank_posting["units"]["currency"] == "USD"

    def test_price_and_cost_together(self, beancount):
        """Cost and price on the same posting: {cost} @ price."""
        source = """\
2024-01-01 open Assets:Brokerage AAPL
2024-01-01 open Assets:Bank USD
2024-01-01 open Income:Gains USD

2024-06-01 * "Buy shares"
  Assets:Brokerage  10 AAPL {150.00 USD}
  Assets:Bank      -1500.00 USD

2024-09-01 * "Sell shares"
  Assets:Brokerage  -10 AAPL {150.00 USD} @ 170.00 USD
  Assets:Bank       1700.00 USD
  Income:Gains      -200.00 USD
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        txns = [d for d in result.directives if d.type == "transaction"]
        sell_txn = txns[1]
        aapl_posting = [p for p in sell_txn.data["postings"]
                        if p["account"] == "Assets:Brokerage"][0]
        assert aapl_posting["cost"] is not None
        assert aapl_posting["price"] is not None
        assert aapl_posting["price"]["number"] == "170.00"

    def test_conversion_with_balance_check(self, beancount):
        """Balance assertion after a currency exchange."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Assets:Foreign EUR

2024-01-15 * "Exchange"
  Assets:Foreign  100.00 EUR @ 1.10 USD
  Assets:Bank    -110.00 USD

2024-01-16 balance Assets:Foreign 100.00 EUR
2024-01-16 balance Assets:Bank   -110.00 USD
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0

    def test_multiple_conversions(self, beancount):
        """Chain of exchanges — verify balances hold."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Assets:EUR EUR
2024-01-01 open Assets:GBP GBP

2024-01-15 * "USD to EUR"
  Assets:EUR      100.00 EUR @ 1.10 USD
  Assets:Bank    -110.00 USD

2024-01-16 * "USD to GBP"
  Assets:GBP       50.00 GBP @ 1.30 USD
  Assets:Bank     -65.00 USD

2024-01-17 balance Assets:Bank -175.00 USD
2024-01-17 balance Assets:EUR   100.00 EUR
2024-01-17 balance Assets:GBP    50.00 GBP
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0

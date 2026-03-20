"""Tests for price directives and price annotations.

Fava wraps beancount's price maps (FavaPriceMap) — this is a known
tight-coupling point.
"""


class TestPriceDirective:

    def test_simple_price(self, beancount):
        """A price directive establishes an exchange rate."""
        source = """\
2024-01-15 price AAPL 150.00 USD
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        # price directives become their own type
        prices = [d for d in result.directives if d.type == "price"]
        assert len(prices) == 1

    def test_multiple_prices(self, beancount):
        """Multiple price directives for the same commodity on different dates."""
        source = """\
2024-01-15 price AAPL 150.00 USD
2024-02-15 price AAPL 160.00 USD
2024-03-15 price AAPL 170.00 USD
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        prices = [d for d in result.directives if d.type == "price"]
        assert len(prices) == 3

    def test_price_from_transaction(self, beancount):
        """Price annotations on transactions should be parsed."""
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
        eur_posting = [
            p for p in txn.data["postings"] if p["account"] == "Assets:Foreign"
        ][0]
        assert eur_posting["price"]["number"] == "1.10"
        assert eur_posting["price"]["currency"] == "USD"

    def test_total_price(self, beancount):
        """Total price syntax uses @@."""
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
        eur_posting = [
            p for p in txn.data["postings"] if p["account"] == "Assets:Foreign"
        ][0]
        # Total price of 110 for 100 units = 1.1 per unit
        from decimal import Decimal

        assert Decimal(eur_posting["price"]["number"]) == Decimal("1.1")

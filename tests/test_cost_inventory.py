"""Tests for cost basis, lot tracking, and inventory semantics.

This is where Martin says the 0.8→1.0 difficulty lives, and where TurboBean
is knowingly diverging from beancount v2/v3 behavior.
"""


class TestCostBasis:
    """Basic cost specification on postings."""

    def test_buy_at_cost(self, beancount):
        """Buying a commodity at cost should record the cost basis."""
        source = """\
2024-01-01 open Assets:Brokerage
2024-01-01 open Assets:Bank USD

2024-01-15 * "Buy stock"
  Assets:Brokerage  10 AAPL {150.00 USD}
  Assets:Bank      -1500.00 USD
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0

        txns = [d for d in result.directives if d.type == "transaction"]
        assert len(txns) == 1
        posting = txns[0].data["postings"][0]
        assert posting["units"]["number"] == "10"
        assert posting["units"]["currency"] == "AAPL"
        assert posting["cost"]["number"] == "150.00"
        assert posting["cost"]["currency"] == "USD"

    def test_sell_at_cost_with_price(self, beancount):
        """Selling at cost with a price annotation should compute gains."""
        source = """\
2024-01-01 open Assets:Brokerage
2024-01-01 open Assets:Bank USD
2024-01-01 open Income:Gains USD

2024-01-15 * "Buy stock"
  Assets:Brokerage  10 AAPL {150.00 USD}
  Assets:Bank      -1500.00 USD

2024-06-15 * "Sell stock"
  Assets:Brokerage  -5 AAPL {150.00 USD} @ 180.00 USD
  Assets:Bank        900.00 USD
  Income:Gains
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0

        sell = [d for d in result.directives if d.type == "transaction"][1]
        brokerage_posting = sell.data["postings"][0]
        assert brokerage_posting["cost"]["number"] == "150.00"
        assert brokerage_posting["price"]["number"] == "180.00"

        # Income:Gains should be auto-filled: -(5 * 180 - 5 * 150) = -150.00
        gains_posting = [
            p for p in sell.data["postings"] if p["account"] == "Income:Gains"
        ][0]
        assert gains_posting["units"]["number"] == "-150.00"

    def test_total_cost(self, beancount):
        """Total cost syntax uses double braces: {{...}}."""
        source = """\
2024-01-01 open Assets:Brokerage
2024-01-01 open Assets:Bank USD

2024-01-15 * "Buy stock"
  Assets:Brokerage  10 AAPL {{1500.00 USD}}
  Assets:Bank      -1500.00 USD
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0

        txn = [d for d in result.directives if d.type == "transaction"][0]
        posting = txn.data["postings"][0]
        # Total cost of 1500 for 10 shares = 150 per share
        assert posting["cost"]["number"] == "150.00"


class TestLotMatching:
    """Lot matching: how the implementation chooses which lot to reduce."""

    def test_explicit_cost_match(self, beancount):
        """When cost is specified explicitly, it must match an existing lot."""
        source = """\
2024-01-01 open Assets:Brokerage
2024-01-01 open Assets:Bank USD
2024-01-01 open Income:Gains USD

2024-01-15 * "Buy lot 1"
  Assets:Brokerage  10 AAPL {100.00 USD}
  Assets:Bank

2024-02-15 * "Buy lot 2"
  Assets:Brokerage  10 AAPL {120.00 USD}
  Assets:Bank

2024-06-15 * "Sell from lot 1"
  Assets:Brokerage  -5 AAPL {100.00 USD} @ 150.00 USD
  Assets:Bank  750.00 USD
  Income:Gains
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0

    def test_ambiguous_lot_match_error(self, beancount):
        """Selling without specifying cost when multiple lots exist should error."""
        source = """\
2024-01-01 open Assets:Brokerage
2024-01-01 open Assets:Bank USD

2024-01-15 * "Buy lot 1"
  Assets:Brokerage  10 AAPL {100.00 USD}
  Assets:Bank

2024-02-15 * "Buy lot 2"
  Assets:Brokerage  10 AAPL {120.00 USD}
  Assets:Bank

2024-06-15 * "Sell - ambiguous"
  Assets:Brokerage  -5 AAPL {} @ 150.00 USD
  Assets:Bank  750.00 USD
"""
        result = beancount.parse_string(source)
        # Default booking method is STRICT, which requires unambiguous match
        assert len(result.errors) > 0


class TestBookingMethods:
    """Account booking methods control lot matching behavior."""

    def test_fifo_booking(self, beancount):
        """FIFO booking should sell oldest lots first."""
        source = """\
2024-01-01 open Assets:Brokerage "FIFO"
2024-01-01 open Assets:Bank USD
2024-01-01 open Income:Gains USD

2024-01-15 * "Buy lot 1 at 100"
  Assets:Brokerage  10 AAPL {100.00 USD}
  Assets:Bank

2024-02-15 * "Buy lot 2 at 120"
  Assets:Brokerage  10 AAPL {120.00 USD}
  Assets:Bank

2024-06-15 * "Sell 5 FIFO"
  Assets:Brokerage  -5 AAPL {} @ 150.00 USD
  Assets:Bank  750.00 USD
  Income:Gains
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0

        sell = [d for d in result.directives if d.type == "transaction"][2]
        brokerage = [
            p for p in sell.data["postings"]
            if p["account"] == "Assets:Brokerage"
        ][0]
        # FIFO: should have matched lot at 100.00
        assert brokerage["cost"]["number"] == "100.00"

    def test_lifo_booking(self, beancount):
        """LIFO booking should sell newest lots first."""
        source = """\
2024-01-01 open Assets:Brokerage "LIFO"
2024-01-01 open Assets:Bank USD
2024-01-01 open Income:Gains USD

2024-01-15 * "Buy lot 1 at 100"
  Assets:Brokerage  10 AAPL {100.00 USD}
  Assets:Bank

2024-02-15 * "Buy lot 2 at 120"
  Assets:Brokerage  10 AAPL {120.00 USD}
  Assets:Bank

2024-06-15 * "Sell 5 LIFO"
  Assets:Brokerage  -5 AAPL {} @ 150.00 USD
  Assets:Bank  750.00 USD
  Income:Gains
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0

        sell = [d for d in result.directives if d.type == "transaction"][2]
        brokerage = [
            p for p in sell.data["postings"]
            if p["account"] == "Assets:Brokerage"
        ][0]
        # LIFO: should have matched lot at 120.00
        assert brokerage["cost"]["number"] == "120.00"

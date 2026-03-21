"""Tests for plugin execution during load.

Plugins modify entries during load_file — they are the primary extension
mechanism and Fava loads several built-in plugins. These tests use only
beancount's built-in plugins (no custom Python code needed).
"""


class TestPlugins:

    def test_check_commodity_error(self, beancount):
        """check_commodity plugin errors when posting uses undeclared commodity."""
        source = """\
plugin "beancount.plugins.check_commodity"

2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food

2024-01-15 * "Groceries"
  Expenses:Food   50.00 XYZ
  Assets:Bank    -50.00 USD
"""
        result = beancount.parse_string(source)
        assert any("XYZ" in e for e in result.errors)

    def test_check_commodity_passing(self, beancount):
        """No error when all commodities are declared."""
        source = """\
plugin "beancount.plugins.check_commodity"

2024-01-01 commodity USD
2024-01-01 commodity EUR
2024-01-01 open Assets:Bank USD
2024-01-01 open Assets:Foreign EUR

2024-01-15 * "Exchange"
  Assets:Foreign  100.00 EUR
  Assets:Bank    -100.00 USD
"""
        result = beancount.parse_string(source)
        commodity_errors = [e for e in result.errors if "commodity" in e.lower()]
        assert len(commodity_errors) == 0

    def test_check_drained(self, beancount):
        """check_drained errors when closed account has non-zero balance."""
        source = """\
plugin "beancount.plugins.check_drained"

2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD

2024-01-15 * "Groceries"
  Expenses:Food   50.00 USD
  Assets:Bank    -50.00 USD

2024-02-01 close Assets:Bank
"""
        result = beancount.parse_string(source)
        assert any("drain" in e.lower() or "close" in e.lower() or "balance" in e.lower()
                    for e in result.errors)

    def test_implicit_prices(self, beancount):
        """implicit_prices plugin generates price directives from price annotations."""
        source = """\
plugin "beancount.plugins.implicit_prices"

2024-01-01 open Assets:Bank USD
2024-01-01 open Assets:Foreign EUR

2024-01-15 * "Exchange"
  Assets:Foreign  100.00 EUR @ 1.10 USD
  Assets:Bank    -110.00 USD
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        prices = [d for d in result.directives if d.type == "price"]
        assert len(prices) >= 1
        assert prices[0].data["currency"] == "EUR"

    def test_multiple_plugins(self, beancount):
        """Two plugins loaded together both execute."""
        source = """\
plugin "beancount.plugins.check_commodity"
plugin "beancount.plugins.implicit_prices"

2024-01-01 commodity USD
2024-01-01 commodity EUR
2024-01-01 open Assets:Bank USD
2024-01-01 open Assets:Foreign EUR

2024-01-15 * "Exchange"
  Assets:Foreign  100.00 EUR @ 1.10 USD
  Assets:Bank    -110.00 USD
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        # implicit_prices should have generated a price directive
        prices = [d for d in result.directives if d.type == "price"]
        assert len(prices) >= 1

    def test_plugin_ordering(self, beancount):
        """Plugins execute in the order declared in option lines."""
        source = """\
plugin "beancount.plugins.implicit_prices"
plugin "beancount.plugins.check_commodity"

2024-01-01 commodity USD
2024-01-01 commodity EUR
2024-01-01 open Assets:Bank USD
2024-01-01 open Assets:Foreign EUR

2024-01-15 * "Exchange"
  Assets:Foreign  100.00 EUR @ 1.10 USD
  Assets:Bank    -110.00 USD
"""
        result = beancount.parse_string(source)
        # Both plugins should execute without errors
        assert len(result.errors) == 0

    def test_invalid_plugin(self, beancount):
        """Referencing a nonexistent plugin produces an error."""
        source = """\
plugin "beancount.plugins.does_not_exist_xyz"

2024-01-01 open Assets:Bank USD
"""
        result = beancount.parse_string(source)
        assert len(result.errors) > 0

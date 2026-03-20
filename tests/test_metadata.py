"""Tests for metadata on directives and postings.

Fava reads metadata extensively for display and filtering. Metadata
handling is a common source of subtle divergence between implementations.
"""


class TestTransactionMetadata:

    def test_transaction_level_metadata(self, beancount):
        """Metadata key-value pairs on a transaction."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD

2024-01-15 * "Lunch"
  category: "food"
  Expenses:Food  12.50 USD
  Assets:Bank
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        txn = [d for d in result.directives if d.type == "transaction"][0]
        assert txn.meta.get("category") == "food"

    def test_posting_level_metadata(self, beancount):
        """Metadata on individual postings."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD

2024-01-15 * "Lunch"
  Expenses:Food  12.50 USD
    receipt: "lunch-receipt.pdf"
  Assets:Bank
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        txn = [d for d in result.directives if d.type == "transaction"][0]
        food_posting = [
            p for p in txn.data["postings"] if p["account"] == "Expenses:Food"
        ][0]
        assert food_posting["meta"].get("receipt") == "lunch-receipt.pdf"

    def test_numeric_metadata(self, beancount):
        """Numeric metadata values are stored as Decimals (serialized as strings)."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD

2024-01-15 * "Lunch"
  rating: 5
  Expenses:Food  12.50 USD
  Assets:Bank
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        txn = [d for d in result.directives if d.type == "transaction"][0]
        # Beancount stores numeric metadata as Decimal; our adapter serializes to string
        assert txn.meta.get("rating") == "5"


class TestDirectiveMetadata:

    def test_open_metadata(self, beancount):
        """Metadata on an open directive."""
        source = """\
2024-01-01 open Assets:Bank USD
  institution: "First National"
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        assert result.directives[0].meta.get("institution") == "First National"

    def test_commodity_metadata(self, beancount):
        """Metadata on a commodity directive (common for price sources)."""
        source = """\
2024-01-01 commodity AAPL
  name: "Apple Inc."
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        commodities = [d for d in result.directives if d.type == "commodity"]
        assert commodities[0].meta.get("name") == "Apple Inc."

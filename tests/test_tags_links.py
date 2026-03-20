"""Tests for tags and links on transactions.

Tags (#tag) and links (^link) are used by Fava for filtering and grouping.
"""


class TestTags:

    def test_single_tag(self, beancount):
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD

2024-01-15 * "Lunch" #food
  Expenses:Food  12.50 USD
  Assets:Bank
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        txn = [d for d in result.directives if d.type == "transaction"][0]
        assert "food" in txn.data["tags"]

    def test_multiple_tags(self, beancount):
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD

2024-01-15 * "Lunch" #food #work #reimbursable
  Expenses:Food  12.50 USD
  Assets:Bank
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        txn = [d for d in result.directives if d.type == "transaction"][0]
        assert set(txn.data["tags"]) == {"food", "work", "reimbursable"}

    def test_pushtag_poptag(self, beancount):
        """pushtag/poptag applies tags to all transactions in a range."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD
2024-01-01 open Expenses:Transport USD

pushtag #trip

2024-01-15 * "Lunch"
  Expenses:Food  12.50 USD
  Assets:Bank

2024-01-15 * "Taxi"
  Expenses:Transport  25.00 USD
  Assets:Bank

poptag #trip

2024-01-20 * "Not trip"
  Expenses:Food  10.00 USD
  Assets:Bank
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        txns = [d for d in result.directives if d.type == "transaction"]
        assert "trip" in txns[0].data["tags"]
        assert "trip" in txns[1].data["tags"]
        assert "trip" not in txns[2].data["tags"]


class TestLinks:

    def test_single_link(self, beancount):
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD

2024-01-15 * "Lunch" ^invoice-123
  Expenses:Food  12.50 USD
  Assets:Bank
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        txn = [d for d in result.directives if d.type == "transaction"][0]
        assert "invoice-123" in txn.data["links"]

    def test_tags_and_links_combined(self, beancount):
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD

2024-01-15 * "Lunch" #food ^invoice-123
  Expenses:Food  12.50 USD
  Assets:Bank
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        txn = [d for d in result.directives if d.type == "transaction"][0]
        assert "food" in txn.data["tags"]
        assert "invoice-123" in txn.data["links"]

"""Cross-implementation parse tests.

These tests use the parametrized `implementation` fixture to verify that
all available implementations agree on parse-level behavior. Only tests
syntax/parsing — no booking, interpolation, or plugin assertions.
"""

import pytest

from implementations.adapter import CAP_PARSE


@pytest.mark.requires_capability(CAP_PARSE)
class TestOpenDirective:

    def test_open_with_currencies(self, implementation):
        source = '2024-01-01 open Assets:Bank USD, EUR\n'
        result = implementation.parse_string(source)
        opens = [d for d in result.directives if d.type == "open"]
        assert len(opens) == 1
        assert opens[0].data["account"] == "Assets:Bank"
        assert sorted(opens[0].data["currencies"]) == ["EUR", "USD"]

    def test_open_without_currencies(self, implementation):
        source = '2024-01-01 open Expenses:Food\n'
        result = implementation.parse_string(source)
        opens = [d for d in result.directives if d.type == "open"]
        assert len(opens) == 1
        assert opens[0].data["account"] == "Expenses:Food"
        assert opens[0].data["currencies"] == []


@pytest.mark.requires_capability(CAP_PARSE)
class TestCloseDirective:

    def test_simple_close(self, implementation):
        source = """\
2024-01-01 open Assets:Bank USD
2024-12-31 close Assets:Bank
"""
        result = implementation.parse_string(source)
        closes = [d for d in result.directives if d.type == "close"]
        assert len(closes) == 1
        assert closes[0].data["account"] == "Assets:Bank"
        assert closes[0].date == "2024-12-31"


@pytest.mark.requires_capability(CAP_PARSE)
class TestTransactionFields:

    def test_payee_and_narration(self, implementation):
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD

2024-01-15 * "Grocery Store" "Weekly groceries"
  Expenses:Food  50.00 USD
  Assets:Bank  -50.00 USD
"""
        result = implementation.parse_string(source)
        txns = [d for d in result.directives if d.type == "transaction"]
        assert len(txns) == 1
        assert txns[0].data["payee"] == "Grocery Store"
        assert txns[0].data["narration"] == "Weekly groceries"
        assert txns[0].data["flag"] == "*"

    def test_narration_only(self, implementation):
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD

2024-01-15 * "Just narration"
  Expenses:Food  50.00 USD
  Assets:Bank  -50.00 USD
"""
        result = implementation.parse_string(source)
        txns = [d for d in result.directives if d.type == "transaction"]
        assert len(txns) == 1
        assert txns[0].data["payee"] is None
        assert txns[0].data["narration"] == "Just narration"

    def test_pending_flag(self, implementation):
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD

2024-01-15 ! "Pending"
  Expenses:Food  50.00 USD
  Assets:Bank  -50.00 USD
"""
        result = implementation.parse_string(source)
        txns = [d for d in result.directives if d.type == "transaction"]
        assert len(txns) == 1
        assert txns[0].data["flag"] == "!"


@pytest.mark.requires_capability(CAP_PARSE)
class TestTagsAndLinks:

    def test_inline_tags(self, implementation):
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD

2024-01-15 * "Test" #trip #vacation
  Expenses:Food  50.00 USD
  Assets:Bank  -50.00 USD
"""
        result = implementation.parse_string(source)
        txns = [d for d in result.directives if d.type == "transaction"]
        assert len(txns) == 1
        assert sorted(txns[0].data["tags"]) == ["trip", "vacation"]

    def test_inline_links(self, implementation):
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD

2024-01-15 * "Test" ^invoice-123 ^receipt-456
  Expenses:Food  50.00 USD
  Assets:Bank  -50.00 USD
"""
        result = implementation.parse_string(source)
        txns = [d for d in result.directives if d.type == "transaction"]
        assert len(txns) == 1
        assert sorted(txns[0].data["links"]) == ["invoice-123", "receipt-456"]


@pytest.mark.requires_capability(CAP_PARSE)
class TestPostingAmounts:

    def test_explicit_amounts(self, implementation):
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD

2024-01-15 * "Test"
  Expenses:Food  42.50 USD
  Assets:Bank  -42.50 USD
"""
        result = implementation.parse_string(source)
        txns = [d for d in result.directives if d.type == "transaction"]
        assert len(txns) == 1
        postings = txns[0].data["postings"]
        assert len(postings) == 2
        assert postings[0]["account"] == "Expenses:Food"
        assert postings[0]["units"]["number"] == "42.50"
        assert postings[0]["units"]["currency"] == "USD"
        assert postings[1]["account"] == "Assets:Bank"
        assert postings[1]["units"]["number"] == "-42.50"
        assert postings[1]["units"]["currency"] == "USD"


@pytest.mark.requires_capability(CAP_PARSE)
class TestBalanceDirective:

    def test_simple_balance(self, implementation):
        source = """\
2024-01-01 open Assets:Bank USD
2024-02-01 balance Assets:Bank 100.00 USD
"""
        result = implementation.parse_string(source)
        balances = [d for d in result.directives if d.type == "balance"]
        assert len(balances) == 1
        assert balances[0].data["account"] == "Assets:Bank"
        assert balances[0].data["amount"]["number"] == "100.00"
        assert balances[0].data["amount"]["currency"] == "USD"


@pytest.mark.requires_capability(CAP_PARSE)
class TestNoteDirective:

    def test_simple_note(self, implementation):
        source = """\
2024-01-01 open Assets:Bank USD
2024-02-01 note Assets:Bank "Account opened"
"""
        result = implementation.parse_string(source)
        notes = [d for d in result.directives if d.type == "note"]
        assert len(notes) == 1
        assert notes[0].data["account"] == "Assets:Bank"
        assert notes[0].data["comment"] == "Account opened"


@pytest.mark.requires_capability(CAP_PARSE)
class TestEventDirective:

    def test_simple_event(self, implementation):
        source = '2024-01-15 event "location" "New York"\n'
        result = implementation.parse_string(source)
        events = [d for d in result.directives if d.type == "event"]
        assert len(events) == 1
        assert events[0].data["type"] == "location"
        assert events[0].data["description"] == "New York"


@pytest.mark.requires_capability(CAP_PARSE)
class TestCommodityDirective:

    def test_simple_commodity(self, implementation):
        source = '2024-01-01 commodity USD\n'
        result = implementation.parse_string(source)
        commodities = [d for d in result.directives if d.type == "commodity"]
        assert len(commodities) == 1
        assert commodities[0].data["currency"] == "USD"


@pytest.mark.requires_capability(CAP_PARSE)
class TestPriceDirective:

    def test_simple_price(self, implementation):
        source = '2024-01-15 price USD 0.85 EUR\n'
        result = implementation.parse_string(source)
        prices = [d for d in result.directives if d.type == "price"]
        assert len(prices) == 1
        assert prices[0].data["currency"] == "USD"
        assert prices[0].data["amount"]["number"] == "0.85"
        assert prices[0].data["amount"]["currency"] == "EUR"


@pytest.mark.requires_capability(CAP_PARSE)
class TestMetadata:

    def test_directive_metadata(self, implementation):
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD

2024-01-15 * "Test"
  memo: "important"
  Expenses:Food  50.00 USD
  Assets:Bank  -50.00 USD
"""
        result = implementation.parse_string(source)
        txns = [d for d in result.directives if d.type == "transaction"]
        assert len(txns) == 1
        assert txns[0].meta.get("memo") == "important"


@pytest.mark.requires_capability(CAP_PARSE)
class TestOptions:

    def test_title_option(self, implementation):
        source = """\
option "title" "My Ledger"
2024-01-01 open Assets:Bank USD
"""
        result = implementation.parse_string(source)
        assert result.options.get("title") == "My Ledger"

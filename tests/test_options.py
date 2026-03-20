"""Tests for beancount options parsing.

Fava reads specific options from the options_map. Implementations must
parse and return these correctly.
"""


class TestOptions:

    def test_operating_currency(self, beancount):
        source = """\
option "operating_currency" "USD"
option "operating_currency" "EUR"
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        oc = result.options.get("operating_currency")
        assert isinstance(oc, list)
        assert "USD" in oc
        assert "EUR" in oc

    def test_title_option(self, beancount):
        source = """\
option "title" "My Ledger"
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        assert result.options.get("title") == "My Ledger"

    def test_account_types(self, beancount):
        """Custom account type names should be reflected in options."""
        source = """\
option "name_assets" "Aktiva"
option "name_liabilities" "Verbindlichkeiten"
"""
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        assert result.options.get("name_assets") == "Aktiva"
        assert result.options.get("name_liabilities") == "Verbindlichkeiten"

    def test_invalid_option_error(self, beancount):
        source = """\
option "nonexistent_option" "value"
"""
        result = beancount.parse_string(source)
        assert len(result.errors) > 0

"""Tests for account name handling.

Account names are colon-separated with specific rules about valid
components. Implementations may diverge on edge cases.
"""

from hypothesis import given, settings

from strategies import accounts


class TestAccountValidation:

    def test_standard_roots(self, beancount):
        """All five standard root account types should be accepted."""
        roots = ["Assets", "Liabilities", "Equity", "Income", "Expenses"]
        for root in roots:
            source = f"2024-01-01 open {root}:Test USD\n"
            result = beancount.parse_string(source)
            assert len(result.errors) == 0, f"Failed for root: {root}"

    def test_deep_account(self, beancount):
        """Deeply nested accounts should parse."""
        source = "2024-01-01 open Assets:Bank:Checking:Primary USD\n"
        result = beancount.parse_string(source)
        assert len(result.errors) == 0
        assert result.directives[0].data["account"] == "Assets:Bank:Checking:Primary"

    def test_account_with_numbers(self, beancount):
        """Account components can contain numbers."""
        source = "2024-01-01 open Assets:Bank123 USD\n"
        result = beancount.parse_string(source)
        assert len(result.errors) == 0

    def test_account_with_dashes(self, beancount):
        """Account components can contain dashes."""
        source = "2024-01-01 open Assets:My-Bank USD\n"
        result = beancount.parse_string(source)
        assert len(result.errors) == 0

    def test_invalid_root_error(self, beancount):
        """An invalid root account type should produce a parse error."""
        source = "2024-01-01 open Invalid:Account USD\n"
        result = beancount.parse_string(source)
        assert len(result.errors) > 0

    def test_duplicate_open_error(self, beancount):
        """Opening the same account twice should error."""
        source = """\
2024-01-01 open Assets:Bank USD
2024-01-02 open Assets:Bank USD
"""
        result = beancount.parse_string(source)
        assert len(result.errors) > 0

    def test_posting_to_unopened_account(self, beancount):
        """Posting to an account that was never opened should error."""
        source = """\
2024-01-15 * "No open"
  Expenses:Food  12.50 USD
  Assets:Bank
"""
        result = beancount.parse_string(source)
        assert len(result.errors) > 0


class TestGenerativeAccounts:

    @given(account=accounts())
    @settings(max_examples=50)
    def test_generated_account_parses(self, beancount, account):
        """Any generated account name should parse as a valid open directive."""
        source = f"2024-01-01 open {account} USD\n"
        result = beancount.parse_string(source)
        assert len(result.errors) == 0, (
            f"Failed for account: {account}\nErrors: {result.errors}"
        )

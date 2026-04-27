"""Tests for BQL (Bean Query Language) execution.

Fava's Query report executes BQL queries — divergence in query semantics
directly affects what users see.
"""

import pytest


LEDGER = """\
2024-01-01 open Assets:Bank USD
2024-01-01 open Assets:Savings USD
2024-01-01 open Expenses:Food USD
2024-01-01 open Income:Salary USD

2024-01-15 * "Acme Corp" "January salary"
  Assets:Bank     5000.00 USD
  Income:Salary  -5000.00 USD

2024-01-20 * "Grocery Store" "Weekly groceries"
  Expenses:Food   150.00 USD
  Assets:Bank    -150.00 USD

2024-02-01 * "Transfer" "To savings"
  Assets:Savings  1000.00 USD
  Assets:Bank    -1000.00 USD

2024-02-15 * "Acme Corp" "February salary"
  Assets:Bank     5000.00 USD
  Income:Salary  -5000.00 USD
"""


def _skip_if_no_beanquery():
    try:
        import beanquery  # noqa: F401
    except ImportError:
        pytest.skip("beanquery not installed")


class TestBQL:

    def test_select_account_balances(self, beancount):
        """SELECT account, sum(position) GROUP BY account."""
        _skip_if_no_beanquery()
        query = "SELECT account, sum(position) GROUP BY account ORDER BY account"
        result = beancount.execute_query(LEDGER, query)
        assert len(result.errors) == 0
        assert len(result.columns) >= 2
        assert result.columns[0].name == "account"
        assert len(result.rows) > 0
        accounts = [row[0] for row in result.rows]
        assert "Assets:Bank" in accounts

    def test_filter_by_account(self, beancount):
        """WHERE account ~ 'Assets' filters to asset accounts."""
        _skip_if_no_beanquery()
        query = 'SELECT account, sum(position) WHERE account ~ "Assets" GROUP BY account ORDER BY account'
        result = beancount.execute_query(LEDGER, query)
        assert len(result.errors) == 0
        accounts = [row[0] for row in result.rows]
        assert all("Assets" in a for a in accounts)

    def test_date_filtering(self, beancount):
        """WHERE date >= 2024-02-01 filters by date."""
        _skip_if_no_beanquery()
        query = "SELECT date, narration WHERE date >= 2024-02-01"
        result = beancount.execute_query(LEDGER, query)
        assert len(result.errors) == 0
        assert len(result.rows) >= 2  # Feb transfer + Feb salary

    def test_transaction_narration(self, beancount):
        """SELECT narration WHERE flag = '*'."""
        _skip_if_no_beanquery()
        query = 'SELECT DISTINCT narration WHERE flag = "*" ORDER BY narration'
        result = beancount.execute_query(LEDGER, query)
        assert len(result.errors) == 0
        narrations = [row[0] for row in result.rows]
        assert "January salary" in narrations or any("salary" in n.lower() for n in narrations)

    def test_count_aggregation(self, beancount):
        """SELECT count(*) returns total posting count."""
        _skip_if_no_beanquery()
        query = "SELECT count(*)"
        result = beancount.execute_query(LEDGER, query)
        assert len(result.errors) == 0
        assert len(result.rows) == 1
        count = int(result.rows[0][0])
        assert count > 0

    def test_empty_result(self, beancount):
        """Query that matches nothing returns empty rows."""
        _skip_if_no_beanquery()
        query = 'SELECT narration WHERE narration = "nonexistent_xyz_12345"'
        result = beancount.execute_query(LEDGER, query)
        assert len(result.errors) == 0
        assert len(result.rows) == 0

    def test_syntax_error(self, beancount):
        """Invalid BQL produces an error."""
        _skip_if_no_beanquery()
        query = "SELECTT INVALID SYNTAX HERE!!!"
        result = beancount.execute_query(LEDGER, query)
        assert len(result.errors) > 0


class TestBQLColumnTypes:
    """Typed-column regression tests: QueryResult.columns carries name + datatype."""

    def test_column_info_shape(self, beancount):
        """Each column is a ColumnInfo with name and datatype fields."""
        _skip_if_no_beanquery()
        result = beancount.execute_query(LEDGER, "SELECT account, sum(position) GROUP BY account")
        assert len(result.errors) == 0
        for col in result.columns:
            assert hasattr(col, "name") and isinstance(col.name, str) and col.name
            assert hasattr(col, "datatype") and isinstance(col.datatype, str) and col.datatype

    def test_str_column_type(self, beancount):
        """account and narration columns are typed 'str'."""
        _skip_if_no_beanquery()
        result = beancount.execute_query(LEDGER, "SELECT account, narration")
        assert len(result.errors) == 0
        by_name = {c.name: c.datatype for c in result.columns}
        assert by_name.get("account") == "str"
        assert by_name.get("narration") == "str"

    def test_inventory_column_type(self, beancount):
        """sum(position) is typed 'Inventory'."""
        _skip_if_no_beanquery()
        result = beancount.execute_query(LEDGER, "SELECT account, sum(position) GROUP BY account")
        assert len(result.errors) == 0
        by_name = {c.name: c.datatype for c in result.columns}
        assert by_name.get("sum(position)") == "Inventory"

    def test_date_column_type(self, beancount):
        """date column is typed 'date'."""
        _skip_if_no_beanquery()
        result = beancount.execute_query(LEDGER, "SELECT date, narration")
        assert len(result.errors) == 0
        by_name = {c.name: c.datatype for c in result.columns}
        assert by_name.get("date") == "date"

    def test_int_column_type(self, beancount):
        """count(*) is typed 'int'."""
        _skip_if_no_beanquery()
        result = beancount.execute_query(LEDGER, "SELECT count(*)")
        assert len(result.errors) == 0
        assert len(result.columns) == 1
        assert result.columns[0].datatype == "int"

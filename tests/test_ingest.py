"""Tests for CAP_INGEST — beangulp Importer ABC compatibility.

run_importer(importer, filepath) calls importer.extract(filepath, existing=[])
and returns extracted directives as a ParseResult. This suite is opt-in via
CAP_INGEST; non-Python adapters are skipped automatically.
"""

import csv
import datetime
from decimal import Decimal
from pathlib import Path

import pytest

import beangulp

from implementations.adapter import CAP_INGEST


FIXTURE_CSV = Path(__file__).parent.parent / "fixtures" / "ingest" / "csv_simple.csv"


class SimpleCsvImporter(beangulp.Importer):
    """Trivial importer: reads date/description/amount rows from a CSV file."""

    def identify(self, filepath: str) -> bool:
        return Path(filepath).name == "csv_simple.csv"

    def account(self, filepath: str) -> str:
        return "Assets:Bank:Checking"

    def extract(self, filepath: str, existing) -> list:
        from beancount.core import data, amount as bc_amount

        entries = []
        with open(filepath, newline="") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                date = datetime.date.fromisoformat(row["date"])
                num = Decimal(row["amount"])
                meta = data.new_metadata(filepath, i + 1)
                txn = data.Transaction(
                    meta=meta,
                    date=date,
                    flag="*",
                    payee=None,
                    narration=row["description"],
                    tags=frozenset(),
                    links=frozenset(),
                    postings=[
                        data.Posting(
                            account="Assets:Bank:Checking",
                            units=bc_amount.Amount(num, "USD"),
                            cost=None,
                            price=None,
                            flag=None,
                            meta={},
                        ),
                    ],
                )
                entries.append(txn)
        return entries


@pytest.fixture(autouse=True)
def require_ingest(beancount):
    if CAP_INGEST not in beancount.capabilities:
        pytest.skip("CAP_INGEST not supported")


class TestRunImporter:

    def test_extracts_correct_count(self, beancount):
        """Trivial CSV importer extracts one transaction per data row."""
        importer = SimpleCsvImporter()
        result = beancount.run_importer(importer, str(FIXTURE_CSV))
        assert len(result.errors) == 0
        txns = [d for d in result.directives if d.type == "transaction"]
        assert len(txns) == 3

    def test_extracts_correct_narrations(self, beancount):
        """Extracted transactions carry narrations from the CSV description column."""
        importer = SimpleCsvImporter()
        result = beancount.run_importer(importer, str(FIXTURE_CSV))
        txns = [d for d in result.directives if d.type == "transaction"]
        narrations = {t.data["narration"] for t in txns}
        assert narrations == {"Grocery Store", "Salary", "Coffee Shop"}

    def test_extracts_correct_dates(self, beancount):
        """Extracted transaction dates match ISO dates in the CSV."""
        importer = SimpleCsvImporter()
        result = beancount.run_importer(importer, str(FIXTURE_CSV))
        txns = [d for d in result.directives if d.type == "transaction"]
        dates = {t.date for t in txns}
        assert dates == {"2024-01-15", "2024-01-20", "2024-01-25"}

    def test_extracts_correct_amounts(self, beancount):
        """Extracted postings have amounts and currencies matching the CSV."""
        importer = SimpleCsvImporter()
        result = beancount.run_importer(importer, str(FIXTURE_CSV))
        txns = [d for d in result.directives if d.type == "transaction"]
        grocery = next(t for t in txns if t.data["narration"] == "Grocery Store")
        posting = grocery.data["postings"][0]
        assert posting["units"]["number"] == "-50.00"
        assert posting["units"]["currency"] == "USD"

        salary = next(t for t in txns if t.data["narration"] == "Salary")
        posting = salary.data["postings"][0]
        assert posting["units"]["number"] == "1000.00"
        assert posting["units"]["currency"] == "USD"

    def test_empty_existing_entries(self, beancount):
        """run_importer passes empty existing entries (no deduplication side-effects)."""
        importer = SimpleCsvImporter()
        result = beancount.run_importer(importer, str(FIXTURE_CSV))
        assert result is not None
        assert isinstance(result.directives, list)

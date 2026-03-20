"""Strategies for generating valid beancount transactions and directives."""

from hypothesis import strategies as st

from strategies.accounts import accounts
from strategies.amounts import currencies, numbers
from strategies.dates import dates

# Simple narrations: printable ASCII, no quotes that would break syntax.
_narrations = st.from_regex(r'[A-Za-z0-9 ]{1,30}', fullmatch=True)


@st.composite
def open_directives(draw):
    """Generate a valid open directive as a beancount string."""
    date = draw(dates)
    account = draw(accounts())
    currency = draw(currencies)
    return f"{date} open {account} {currency}"


@st.composite
def simple_transactions(draw):
    """Generate a simple valid two-posting transaction that balances.

    Generates the required open directives and the transaction itself.
    Returns a complete, self-contained beancount string.
    """
    date = draw(dates)
    narration = draw(_narrations)
    currency = draw(currencies)
    amount = draw(numbers)

    from_account = draw(accounts(roots=["Assets", "Liabilities"]))
    to_account = draw(accounts(roots=["Expenses", "Income"]))

    # Ensure accounts are distinct
    if from_account == to_account:
        to_account = "Expenses:Other"

    # Build complete ledger: opens then transaction
    open_date = "1990-01-01"
    lines = [
        f"{open_date} open {from_account} {currency}",
        f"{open_date} open {to_account} {currency}",
        "",
        f'{date} * "{narration}"',
        f"  {to_account}  {amount} {currency}",
        f"  {from_account}  -{amount} {currency}",
    ]
    return "\n".join(lines)

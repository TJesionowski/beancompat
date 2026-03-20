"""Strategies for generating valid beancount amounts (number + currency).

Beancount currency rules:
- All uppercase letters
- 1-24 characters
- Common: USD, EUR, GBP, JPY, etc.

Numbers:
- Decimal format with optional fractional part
- Can be negative
"""

from decimal import Decimal

from hypothesis import strategies as st

# Use common real currencies to keep generated examples readable.
COMMON_CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CAD", "CHF", "AUD", "BRL"]

currencies = st.sampled_from(COMMON_CURRENCIES)

# Reasonable decimal numbers: avoid extremes that might trigger edge cases
# in formatting but not in semantics. Two decimal places matches most real usage.
numbers = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("999999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)


@st.composite
def amounts(draw):
    """Generate a valid beancount amount (number + currency)."""
    number = draw(numbers)
    currency = draw(currencies)
    return (number, currency)

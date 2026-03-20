"""Strategies for generating valid beancount dates.

Beancount dates are YYYY-MM-DD format. We constrain to a reasonable range.
"""

import datetime

from hypothesis import strategies as st

dates = st.dates(
    min_value=datetime.date(1990, 1, 1),
    max_value=datetime.date(2030, 12, 31),
)

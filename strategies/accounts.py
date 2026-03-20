"""Strategies for generating valid beancount account names.

Beancount account rules:
- Colon-separated components
- First component must be one of: Assets, Liabilities, Equity, Income, Expenses
- Each component starts with an uppercase letter
- Components contain letters, numbers, and dashes
- At least two components (root:leaf)
"""

from hypothesis import strategies as st

ACCOUNT_ROOTS = ["Assets", "Liabilities", "Equity", "Income", "Expenses"]

# A single account component (after the root): starts with uppercase, then
# letters/digits/dashes. Keep it short to avoid bloated examples.
_component = st.from_regex(r"[A-Z][A-Za-z0-9\-]{0,11}", fullmatch=True)


@st.composite
def accounts(draw, roots=None):
    """Generate a valid beancount account name.

    Args:
        roots: Optional list of allowed root account types.
              Defaults to all five standard roots.
    """
    if roots is None:
        roots = ACCOUNT_ROOTS
    root = draw(st.sampled_from(roots))
    depth = draw(st.integers(min_value=1, max_value=3))
    components = [draw(_component) for _ in range(depth)]
    return ":".join([root] + components)

"""Test fixtures for beancompat."""

import pytest

from implementations.beancount import BeancountAdapter


@pytest.fixture(scope="session")
def beancount():
    """Provide the beancount reference adapter.

    Session-scoped: the adapter is stateless, so sharing it across tests
    (including Hypothesis @given tests) is safe and avoids repeated
    availability checks.
    """
    adapter = BeancountAdapter()
    if not adapter.is_available():
        pytest.skip("beancount not available")
    return adapter

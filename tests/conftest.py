"""Test fixtures for beancompat."""

import pytest

from implementations.adapter import CAP_PARSE, CAP_BOOKING
from implementations.beancount import BeancountAdapter
from implementations.beancountparser import BeancountParserAdapter
from implementations.beancountparserlima import BeancountParserLimaAdapter

ADAPTERS = {
    "beancount": BeancountAdapter,
    "beancount-parser": BeancountParserAdapter,
    "beancount-parser-lima": BeancountParserLimaAdapter,
}


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


@pytest.fixture(scope="session")
def beancountparser():
    """Provide the beancount-parser adapter."""
    adapter = BeancountParserAdapter()
    if not adapter.is_available():
        pytest.skip("beancount-parser not available")
    return adapter


@pytest.fixture(scope="session", params=list(ADAPTERS.keys()))
def implementation(request):
    """Parametrized fixture yielding each available adapter."""
    adapter = ADAPTERS[request.param]()
    if not adapter.is_available():
        pytest.skip(f"{request.param} not available")
    return adapter


@pytest.fixture(scope="session")
def all_parsers():
    """Return list of (name, adapter) for all available parse-capable implementations.

    Used by property-based discrepancy tests that compare outputs across
    all implementations simultaneously (not parametrized).
    """
    available = []
    for name, cls in ADAPTERS.items():
        adapter = cls()
        if adapter.is_available() and CAP_PARSE in adapter.capabilities:
            available.append((name, adapter))
    if len(available) < 2:
        pytest.skip("Need at least 2 parse-capable implementations for comparison")
    return available


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "requires_capability(cap): skip if implementation lacks capability"
    )


@pytest.fixture(autouse=True)
def _check_capabilities(request):
    """Skip tests if the implementation lacks a required capability."""
    marker = request.node.get_closest_marker("requires_capability")
    if marker is None:
        return
    impl = request.node.funcargs.get("implementation")
    if impl is None:
        return
    required = set(marker.args)
    missing = required - impl.capabilities
    if missing:
        pytest.skip(f"{impl.name} lacks capabilities: {', '.join(sorted(missing))}")

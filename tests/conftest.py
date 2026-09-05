# tests/conftest.py
import os
import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "network: tests requiring network access")
    config.addinivalue_line("markers", "slow: slow-running tests")


def pytest_collection_modifyitems(config, items):
    run_network = os.environ.get("RUN_NETWORK_TESTS", "0") == "1"
    run_slow = os.environ.get("RUN_SLOW_TESTS", "0") == "1"

    skip_network = pytest.mark.skip(reason="set RUN_NETWORK_TESTS=1 to run")
    skip_slow = pytest.mark.skip(reason="set RUN_SLOW_TESTS=1 to run")

    for item in items:
        if "network" in item.keywords and not run_network:
            item.add_marker(skip_network)
        if "slow" in item.keywords and not run_slow:
            item.add_marker(skip_slow)

# tests/conftest.py
import os

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "network: tests requiring network access")
    config.addinivalue_line("markers", "slow: slow-running tests")
    config.addinivalue_line("markers", "gui: tests nécessitant un display (Xvfb)")


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


@pytest.fixture(scope="session")
def tk_root():
    """Racine tkinter partagée par les tests GUI.

    En CI headless (pas de display), le test est IGNORÉ et non en échec :
    `tk.Tk()` lève `TclError` sur ce type de runner.

    Scope session pour une seule raison : créer plusieurs `Tk()` dans un
    même process est peu fiable (certains builds Windows lèvent
    `invalid command name "tcl_findLibrary"` à la 2e/3e instantiation).
    Un `Toplevel` suffit à tous les tests GUI, qui n'ont pas besoin d'une
    fenêtre top-level.
    """
    import tkinter as tk

    try:
        root = tk.Tk()
    except tk.TclError as exc:  # pas de display
        pytest.skip(f"tkinter indisponible : {exc}")
    root.withdraw()
    yield root
    try:
        root.destroy()
    except tk.TclError:
        pass


@pytest.fixture
def tk_frame(tk_root):
    """Frame Tkinter neuve, détruite après le test."""
    import tkinter as tk

    frame = tk.Frame(tk_root)
    try:
        yield frame
    finally:
        try:
            frame.destroy()
        except tk.TclError:
            pass

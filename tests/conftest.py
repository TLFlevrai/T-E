# tests/conftest.py
"""Configuration pytest partagée."""
import sys
from pathlib import Path
import pytest

# Ajouter le répertoire racine au path pour les imports
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

@pytest.fixture(autouse=True)
def reset_config_singleton():
    """Reset le singleton Config avant chaque test."""
    from src.config import _Config
    _Config._reset_for_testing()
    yield
    _Config._reset_for_testing()

@pytest.fixture
def temp_config(tmp_path):
    """Crée un fichier config.json temporaire."""
    config_path = tmp_path / "config.json"
    config_data = {
        "output_dir": str(tmp_path / "out"),
        "received_subdir": "received",
        "archive_subdir": "old_out",
        "version_file": "extractor_version.txt",
        "language": "en",
        "network": {
            "server_host": "127.0.0.1",
            "server_port": 50000,
            "discovery_port": 50001,
            "broadcast_msg": "PYEXTRACTOR_DISCOVER",
            "reply_msg": "PYEXTRACTOR_HERE",
            "auth_enabled": False,
            "auth_token": "test-token",
            "allowed_extensions": [".txt"]
        },
        "extraction": {
            "include_json": True,
            "include_subdirs": True,
            "show_file_paths": True,
            "include_structure": True,
            "include_txt": False,
            "include_po": True,
            "include_mo": True,
            "include_html": True,
            "include_css": True,
            "include_js": True,
            "ignore_init": False,
            "ignore_git": True,
            "ignore_pycache": True,
            "include_statistics": True,
            "include_file_metadata": True
        },
        "gui": {
            "window_width": 1100,
            "window_height": 750,
            "log_height": 12
        }
    }
    import json
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=2)
    return config_path

@pytest.fixture
def sample_project(tmp_path):
    """Crée un projet d'exemple pour les tests."""
    project = tmp_path / "sample_project"
    project.mkdir()
    
    # Structure
    (project / "main.py").write_text("# Main module\nprint('hello')\n")
    (project / "utils.py").write_text("# Utils\n\ndef helper():\n    return 42\n")
    (project / "config.json").write_text('{"key": "value"}\n')
    (project / "style.css").write_text("body { color: red; }\n")
    (project / "script.js").write_text("console.log('test');\n")
    
    # Sous-dossier
    subdir = project / "subpackage"
    subdir.mkdir()
    (subdir / "__init__.py").write_text("")
    (subdir / "module.py").write_text("# Sub module\n")
    
    # __pycache__ (devrait être ignoré)
    pycache = project / "__pycache__"
    pycache.mkdir()
    (pycache / "main.cpython-311.pyc").write_bytes(b"fake")
    
    # .git (devrait être ignoré)
    gitdir = project / ".git"
    gitdir.mkdir()
    (gitdir / "config").write_text("[core]\n")
    
    return project
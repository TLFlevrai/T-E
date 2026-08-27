# tests/unit/test_config.py
"""Tests pour le module de configuration."""
import pytest
import json
from pathlib import Path

from src.config import get_config, _Config
from src.config.schema import AppConfig, ExtractionOptions, NetworkConfig, GuiConfig


class TestConfigSchema:
    """Tests de validation des schémas Pydantic."""
    
    def test_extraction_options_defaults(self):
        opts = ExtractionOptions()
        assert opts.include_json is True
        assert opts.include_subdirs is True
        assert opts.ignore_pycache is True
        assert opts.ignore_git is False  # Default is False per schema
    
    def test_extraction_options_custom(self):
        opts = ExtractionOptions(include_json=False, ignore_git=False)
        assert opts.include_json is False
        assert opts.ignore_git is False
    
    def test_network_config_validation(self):
        # Port valide
        net = NetworkConfig(server_port=8080, discovery_port=8081)
        assert net.server_port == 8080
        
        # Port invalide (< 1024)
        with pytest.raises(ValueError):
            NetworkConfig(server_port=80)
        
        # Port invalide (> 65535)
        with pytest.raises(ValueError):
            NetworkConfig(server_port=70000)
    
    def test_gui_config_validation(self):
        gui = GuiConfig(window_width=800, window_height=600)
        assert gui.window_width == 800
        
        # Trop petit
        with pytest.raises(ValueError):
            GuiConfig(window_width=300)
        
        # Trop grand
        with pytest.raises(ValueError):
            GuiConfig(window_width=2000)
    
    def test_app_config_full(self):
        cfg = AppConfig(
            output_dir="custom_out",
            language="en",
            network=NetworkConfig(auth_enabled=False),
            extraction=ExtractionOptions(include_txt=True),
            gui=GuiConfig(log_height=15)
        )
        assert cfg.output_dir == "custom_out"
        assert cfg.language == "en"
        assert cfg.network.auth_enabled is False
        assert cfg.extraction.include_txt is True
        assert cfg.gui.log_height == 15


class TestConfigSingleton:
    """Tests du singleton de configuration."""
    
    def test_singleton_instance(self):
        cfg1 = get_config()
        cfg2 = get_config()
        assert cfg1 is cfg2  # Même instance
    
    def test_get_simple_key(self):
        cfg = get_config()
        assert cfg.get("output_dir") == "out"
        assert cfg.get("language") in ("fr", "en")
    
    def test_get_nested_key(self):
        cfg = get_config()
        assert cfg.get("network.server_port") == 50000
        assert cfg.get("extraction.include_json") is True
        assert isinstance(cfg.get("gui.window_width"), int)
        assert cfg.get("gui.window_width") >= 400
    
    def test_get_with_default(self):
        cfg = get_config()
        assert cfg.get("nonexistent.key", "default") == "default"
        assert cfg.get("network.nonexistent", 42) == 42
    
    def test_get_all_returns_immutable(self):
        cfg = get_config()
        all_cfg = cfg.get_all()
        assert isinstance(all_cfg, AppConfig)
        assert all_cfg.output_dir == "out"
    
    def test_reset_for_testing(self):
        cfg1 = get_config()
        _Config._reset_for_testing()
        cfg2 = get_config()
        # Après reset, nouvelle instance mais mêmes valeurs
        assert cfg1 is not cfg2
        assert cfg2.get("output_dir") == "out"


class TestConfigFromFile:
    """Tests de chargement depuis config.json."""
    
    def test_load_from_file(self, temp_config):
        """Test le chargement depuis un fichier personnalisé."""
        # Le fixture temp_config a déjà créé le fichier
        # On doit forcer le rechargement
        _Config._reset_for_testing()
        
        # Modifier temporairement CONFIG_PATH pour pointer vers notre fichier
        import src.config
        original_path = src.config.CONFIG_PATH
        src.config.CONFIG_PATH = temp_config
        
        try:
            cfg = get_config()
            assert cfg.get("output_dir") == str(temp_config.parent / "out")
            assert cfg.get("network.auth_enabled") is False
            assert cfg.get("extraction.include_txt") is False
        finally:
            src.config.CONFIG_PATH = original_path
            _Config._reset_for_testing()


class TestConfigValidation:
    """Tests de validation des valeurs."""
    
    def test_language_values(self):
        cfg = get_config()
        lang = cfg.get("language")
        assert lang in ("fr", "en")
    
    def test_network_ports_range(self):
        cfg = get_config()
        server_port = cfg.get("network.server_port")
        discovery_port = cfg.get("network.discovery_port")
        assert 1024 <= server_port <= 65535
        assert 1024 <= discovery_port <= 65535
    
    def test_gui_dimensions(self):
        cfg = get_config()
        width = cfg.get("gui.window_width")
        height = cfg.get("gui.window_height")
        assert 400 <= width <= 1920
        assert 300 <= height <= 1080


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
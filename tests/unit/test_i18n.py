# tests/unit/test_i18n.py
"""Tests pour le module d'internationalisation."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.i18n import (
    _, pgettext, LazyString, LazyStringContext,
    setup_i18n, reload_translations, change_language,
    get_current_language, register_reload_callback, unregister_reload_callback,
    Translator
)


class TestTranslator:
    """Tests de la classe Translator."""
    
    def test_translator_call(self):
        """Test l'appel direct du traducteur."""
        translator = Translator()
        translator.set_translation(lambda x: f"TRANS:{x}")
        assert translator("hello") == "TRANS:hello"
    
    def test_pgettext_with_context_catalog(self):
        """Test pgettext avec catalogue de contexte."""
        translator = Translator()
        translator.set_context_catalog({
            ("menu", "Fichier"): "File",
            ("button", "Fichier"): "Open",
        })
        assert translator.pgettext("menu", "Fichier") == "File"
        assert translator.pgettext("button", "Fichier") == "Open"
        # Fallback si contexte non trouvé
        assert translator.pgettext("unknown", "Fichier") == "Fichier"
    
    def test_set_translation(self):
        translator = Translator()
        translator.set_translation(lambda x: x.upper())
        assert translator("test") == "TEST"


class TestLazyString:
    """Tests de LazyString (traduction paresseuse)."""
    
    def test_lazy_string_basic(self):
        ls = LazyString("hello")
        assert str(ls) == "hello"  # Pas de traduction par défaut
    
    def test_lazy_string_with_format(self):
        ls = LazyString("File: {}", "test.txt")
        assert str(ls) == "File: test.txt"
    
    def test_lazy_string_format_method(self):
        ls = LazyString("File: {}")
        ls2 = ls.format("test.txt")
        assert isinstance(ls2, LazyString)
        assert str(ls2) == "File: test.txt"
    
    def test_lazy_string_translation(self):
        # Mock la traduction
        import src.i18n as i18n_module
        original_func = i18n_module._._func
        i18n_module._._func = lambda x: f"TRANS:{x}"
        
        try:
            ls = LazyString("hello")
            assert str(ls) == "TRANS:hello"
        finally:
            i18n_module._._func = original_func
    
    def test_lazy_string_eq_hash(self):
        ls1 = LazyString("test")
        ls2 = LazyString("test")
        ls3 = LazyString("other")
        assert ls1 == ls2
        assert ls1 != ls3
        assert hash(ls1) == hash(ls2)


class TestLazyStringContext:
    """Tests de LazyStringContext (traduction contextuelle paresseuse)."""
    
    def test_lazy_string_context_basic(self):
        lsc = LazyStringContext("menu", "Fichier")
        assert str(lsc) == "Fichier"  # Pas de traduction par défaut
    
    def test_lazy_string_context_with_format(self):
        lsc = LazyStringContext("confirmation", "Delete {} ?", "file.txt")
        assert str(lsc) == "Delete file.txt ?"
    
    def test_lazy_string_context_translation(self):
        import src.i18n as i18n_module
        original_catalog = i18n_module._._context_catalog
        i18n_module._._context_catalog = {("menu", "Fichier"): "File"}
        
        try:
            lsc = LazyStringContext("menu", "Fichier")
            assert str(lsc) == "File"
        finally:
            i18n_module._._context_catalog = original_catalog


class TestSetupI18n:
    """Tests de setup_i18n."""
    
    def test_setup_i18n_returns_translator(self):
        translator = setup_i18n()
        assert translator is _
    
    def test_get_current_language(self):
        lang = get_current_language()
        assert lang in ("fr", "en")


class TestReloadTranslations:
    """Tests de rechargement des traductions."""
    
    def test_register_unregister_callback(self):
        called = []
        def callback():
            called.append(True)
        
        register_reload_callback(callback)
        reload_translations()
        assert len(called) == 1
        
        called.clear()
        unregister_reload_callback(callback)
        reload_translations()
        assert len(called) == 0
    
    def test_multiple_callbacks(self):
        calls = []
        def cb1(): calls.append(1)
        def cb2(): calls.append(2)
        
        register_reload_callback(cb1)
        register_reload_callback(cb2)
        reload_translations()
        assert calls == [1, 2]
        
        unregister_reload_callback(cb1)
        calls.clear()
        reload_translations()
        assert calls == [2]


class TestChangeLanguage:
    """Tests de changement de langue."""
    
    def test_change_language_returns_bool(self, tmp_path, monkeypatch):
        """Test que change_language retourne un booléen sans polluer le config.json réel."""
        config_path = tmp_path / "config.json"
        config_path.write_text('{"language": "fr"}', encoding="utf-8")
        monkeypatch.setattr("src.config.CONFIG_PATH", config_path)
        from src.config import _Config
        _Config._reset_for_testing()
        try:
            import src.i18n as i18n_module
            result = i18n_module.change_language("en")
            assert isinstance(result, bool)
        finally:
            _Config._reset_for_testing()


class TestPgettext:
    """Tests de la fonction pgettext."""
    
    def test_pgettext_function(self):
        """Test la fonction de commodité pgettext."""
        import src.i18n as i18n_module
        original_catalog = i18n_module._._context_catalog
        i18n_module._._context_catalog = {("test", "msg"): "translated"}
        
        try:
            result = pgettext("test", "msg")
            assert result == "translated"
        finally:
            i18n_module._._context_catalog = original_catalog
    
    def test_pgettext_fallback(self):
        """Test fallback quand pas de traduction."""
        import src.i18n as i18n_module
        original_catalog = i18n_module._._context_catalog
        i18n_module._._context_catalog = {}
        
        try:
            result = pgettext("unknown", "message")
            assert result == "message"
        finally:
            i18n_module._._context_catalog = original_catalog


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
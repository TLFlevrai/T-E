# tests/unit/test_file_discovery.py
"""Tests unitaires pour FileDiscoveryService (extension list & liste blanche)."""
from __future__ import annotations

from src.config import ExtractionOptions
from src.config.schema import ALLOWED_EXTRA_EXTENSIONS
from src.extractor.file_discovery import FileDiscoveryService


def _extensions(**overrides) -> list[str]:
    """Construit la liste d'extensions d'un service de découverte."""
    return FileDiscoveryService(ExtractionOptions(**overrides))._build_extension_list()


def _make_tree(tmp_path):
    """Crée un dossier avec un fichier par extension testée."""
    files = {
        'main.py': 'print(1)\n',
        'data.json': '{}\n',
        'readme.md': '# Titre\n',
        'notes.rst': 'Titre\n=====\n',
        'pyproject.toml': '[project]\nname = "x"\n',
        'ci.yml': 'on: push\n',
        'setup.cfg': '[metadata]\n',
        'pom.xml': '<project/>\n',
        'deploy.sh': 'echo hi\n',
        'query.sql': 'SELECT 1;\n',
        'app.ts': 'const a = 1;\n',
        'page.vue': '<template/>\n',
        'evil.exe': 'MZ\x90\x00',
    }
    for name, content in files.items():
        (tmp_path / name).write_text(content, encoding='utf-8')
    return tmp_path


class TestBuildExtensionList:
    """Tests de _build_extension_list()."""

    def test_defaults_exclude_md_and_extras(self):
        exts = _extensions()
        assert '.md' not in exts
        assert '.toml' not in exts
        assert '.yml' not in exts
        # Les extensions classiques restent présentes
        assert exts[0] == '.py'
        assert '.json' in exts

    def test_include_md_adds_markdown(self):
        assert '.md' in _extensions(include_md=True)

    def test_extra_extensions_are_appended(self):
        exts = _extensions(extra_extensions=['.toml', '.yaml'])
        assert '.toml' in exts
        assert '.yaml' in exts

    def test_extra_extensions_do_not_duplicate_classics(self):
        exts = _extensions(include_md=True, extra_extensions=['.md', '.toml'])
        assert exts.count('.md') == 1
        assert '.toml' in exts

    def test_extra_extensions_preserves_order_and_uniqueness(self):
        exts = _extensions(extra_extensions=['.toml', '.toml', '.yaml'])
        assert exts.count('.toml') == 1
        assert exts.index('.toml') < exts.index('.yaml')

    def test_extra_extensions_normalized_without_leading_dot(self):
        # Le validateur Pydantic normalise déjà, mais le service doit rester
        # robuste s'il reçoit une liste brute (options construites à la main).
        exts = _extensions(extra_extensions=['toml'])
        assert '.toml' in exts


class TestIsExtensionAllowed:
    """Tests de _is_extension_allowed() (défense en profondeur)."""

    def test_allows_whitelisted(self):
        service = FileDiscoveryService(ExtractionOptions())
        assert service._is_extension_allowed('.toml') is True
        assert service._is_extension_allowed('toml') is True
        assert service._is_extension_allowed('.TOML') is True

    def test_rejects_binary_and_unknown(self):
        service = FileDiscoveryService(ExtractionOptions())
        for bad in ('.exe', '.dll', '.so', '.batx', '', '.', '..'):
            assert service._is_extension_allowed(bad) is False

    def test_rejects_non_string(self):
        service = FileDiscoveryService(ExtractionOptions())
        assert service._is_extension_allowed(None) is False
        assert service._is_extension_allowed(123) is False

    def test_dangerous_ext_never_reaches_extension_list(self):
        """Une config forgée ne doit pas faire sortir un binaire."""
        # model_construct court-circute le validateur : c'est exactement le
        # cas que _is_extension_allowed doit rattraper.
        opts = ExtractionOptions.model_construct(extra_extensions=['.exe', '.toml'])
        exts = FileDiscoveryService(opts)._build_extension_list()
        assert '.exe' not in exts
        assert '.toml' in exts

    def test_whitelist_contains_prompt_extensions(self):
        for ext in ('.toml', '.yaml', '.yml', '.ini', '.cfg', '.xml',
                    '.sh', '.ps1', '.sql', '.ts', '.vue', '.rst', '.md'):
            assert ext in ALLOWED_EXTRA_EXTENSIONS


class TestFindFilesWithNewExtensions:
    """Tests de bout en bout du parcours avec les nouvelles extensions."""

    def test_md_only_when_enabled(self, tmp_path):
        folder = _make_tree(tmp_path)

        off = FileDiscoveryService(ExtractionOptions())
        assert not any(p.name == 'readme.md' for p, _, _ in off.find_files(str(folder)))

        on = FileDiscoveryService(ExtractionOptions(include_md=True))
        assert any(p.name == 'readme.md' for p, _, _ in on.find_files(str(folder)))

    def test_extra_extensions_discovered(self, tmp_path):
        folder = _make_tree(tmp_path)
        service = FileDiscoveryService(
            ExtractionOptions(extra_extensions=['.toml', '.yml', '.xml'])
        )
        names = {p.name for p, _, _ in service.find_files(str(folder))}
        assert {'pyproject.toml', 'ci.yml', 'pom.xml'} <= names
        assert 'setup.cfg' not in names

    def test_exe_never_discovered(self, tmp_path):
        folder = _make_tree(tmp_path)
        service = FileDiscoveryService(
            ExtractionOptions.model_construct(extra_extensions=['.exe', '.md'])
        )
        names = {p.name for p, _, _ in service.find_files(str(folder))}
        assert 'evil.exe' not in names
        assert 'readme.md' in names

    def test_rst_stat_key_is_extra(self):
        """Un .rst passe par extra_extensions : pas de ligne dédiée."""
        service = FileDiscoveryService(ExtractionOptions(extra_extensions=['.rst']))
        assert '.rst' in service._build_extension_list()

    def test_yaml_files_discovered_when_requested(self, tmp_path):
        """Les DEUX extensions YAML doivent être découvertes quand
        extra_extensions contient .yaml ET .yml."""
        folder = tmp_path / "proj"
        folder.mkdir()
        (folder / "ci.yml").write_text("on: push\n", encoding='utf-8')
        (folder / "values.yaml").write_text("name: demo\n", encoding='utf-8')
        (folder / "main.py").write_text("x = 1\n", encoding='utf-8')

        service = FileDiscoveryService(
            ExtractionOptions(extra_extensions=['.yaml', '.yml'])
        )
        exts = service._build_extension_list()
        assert '.yaml' in exts
        assert '.yml' in exts

        names = {p.name for p, _, _ in service.find_files(str(folder))}
        assert {'ci.yml', 'values.yaml'} <= names

    def test_yaml_excluded_by_default(self, tmp_path):
        """Sans extra_extensions, aucun .yaml/.yml n'est extrait."""
        folder = tmp_path / "proj"
        folder.mkdir()
        (folder / "ci.yml").write_text("on: push\n", encoding='utf-8')
        (folder / "values.yaml").write_text("name: demo\n", encoding='utf-8')
        (folder / "main.py").write_text("x = 1\n", encoding='utf-8')

        service = FileDiscoveryService(ExtractionOptions())
        names = {p.name for p, _, _ in service.find_files(str(folder))}
        assert names == {'main.py'}

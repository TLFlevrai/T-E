# tests/unit/test_extensions_support.py
"""Extensions supplémentaires : liste blanche, onglet GUI, presets."""
from __future__ import annotations

import json
import types

import pytest

from src.config import ExtractionOptions
from src.config.schema import ALLOWED_EXTRA_EXTENSIONS
from src.gui.selection.utils import get_allowed_extensions
from src.gui.ui_builder import presets as presets_mod
from src.gui.ui_builder.ui_widgets import (
    EXTRA_EXT_CHOICES,
    apply_extra_extensions,
    collect_extra_extensions,
)


class _FakeVar:
    """Substitut de tk.BooleanVar pour les tests sans display."""

    def __init__(self, value=False):
        self._value = bool(value)

    def get(self):
        return self._value

    def set(self, value):
        self._value = bool(value)


class _FakeUI:
    """UI minimale portant les cases d'extensions avancées."""

    def __init__(self, **flags):
        choice_attrs = {attr for attr, _exts, _label in EXTRA_EXT_CHOICES}
        for attr in choice_attrs:
            setattr(self, attr, _FakeVar(flags.get(attr, False)))
        for key, value in flags.items():
            if key not in choice_attrs:
                setattr(self, key, _FakeVar(value))


class TestExtraExtensionChoices:
    """Cohérence entre l'UI et la liste blanche."""

    def test_every_choice_is_whitelisted(self):
        for _attr, exts, _label in EXTRA_EXT_CHOICES:
            for ext in exts:
                assert ext in ALLOWED_EXTRA_EXTENSIONS, ext

    def test_choices_are_unique(self):
        seen = [e for _a, exts, _l in EXTRA_EXT_CHOICES for e in exts]
        assert len(seen) == len(set(seen))

    def test_prompt_extensions_present(self):
        covered = {e for _a, exts, _l in EXTRA_EXT_CHOICES for e in exts}
        for ext in ('.toml', '.yaml', '.yml', '.ini', '.cfg', '.xml',
                    '.sh', '.ps1', '.sql', '.ts', '.vue', '.rst'):
            assert ext in covered

    def test_no_binary_in_whitelist(self):
        for ext in ('.exe', '.dll', '.so', '.pyd', '.bin', '.msi', '.apk'):
            assert ext not in ALLOWED_EXTRA_EXTENSIONS


class TestCollectExtraExtensions:
    """Allers-retours cases à cocher <-> extra_extensions."""

    def test_none_checked(self):
        assert collect_extra_extensions(_FakeUI()) == []

    def test_single_checked(self):
        ui = _FakeUI(extra_ext_toml=True)
        assert collect_extra_extensions(ui) == ['.toml']

    def test_multi_extension_box(self):
        """Une case YAML couvre .yaml ET .yml."""
        ui = _FakeUI(extra_ext_yaml=True)
        assert collect_extra_extensions(ui) == ['.yaml', '.yml']

    def test_ini_box_covers_ini_and_cfg(self):
        assert collect_extra_extensions(_FakeUI(extra_ext_ini=True)) == ['.ini', '.cfg']

    def test_multiple_boxes_order_is_stable(self):
        ui = _FakeUI(extra_ext_xml=True, extra_ext_toml=True)
        assert collect_extra_extensions(ui) == ['.toml', '.xml']

    def test_apply_then_collect_roundtrip(self):
        ui = _FakeUI()
        apply_extra_extensions(ui, ['.sh', '.sql', '.rst'])
        assert collect_extra_extensions(ui) == ['.sh', '.sql', '.rst']

    def test_apply_is_idempotent(self):
        ui = _FakeUI()
        apply_extra_extensions(ui, ['.toml', '.yaml'])
        first = collect_extra_extensions(ui)
        apply_extra_extensions(ui, ['.toml', '.yaml'])
        assert collect_extra_extensions(ui) == first

    def test_apply_empty_clears(self):
        ui = _FakeUI(extra_ext_toml=True, extra_ext_xml=True)
        apply_extra_extensions(ui, [])
        assert collect_extra_extensions(ui) == []

    def test_apply_ignores_unknown_extension(self):
        """Un .exe en config ne coche aucune case."""
        ui = _FakeUI()
        apply_extra_extensions(ui, ['.exe', '.toml'])
        assert collect_extra_extensions(ui) == ['.toml']

    def test_apply_tolerates_none(self):
        ui = _FakeUI()
        apply_extra_extensions(ui, None)
        assert collect_extra_extensions(ui) == []

    def test_missing_attributes_are_ignored(self):
        """Sans cases (extraction headless), aucune exception."""

        class _Bare:
            pass

        assert collect_extra_extensions(_Bare()) == []
        apply_extra_extensions(_Bare(), ['.toml'])


class TestPresets:
    """Presets d'export."""

    def test_full_enables_md_and_all_extra(self):
        values = presets_mod.preset_options('full')
        assert values['include_md'] is True
        assert set(values['extra_extensions']) == set(presets_mod.ALL_EXTRA_EXTENSIONS)

    def test_minimal_disables_md_and_extras(self):
        values = presets_mod.preset_options('minimal')
        assert values['include_md'] is False
        assert values['extra_extensions'] == []

    @pytest.mark.parametrize('preset', ['python_only', 'web_assets', 'minimal'])
    def test_other_presets_disable_extras(self, preset):
        assert presets_mod.preset_options(preset)['extra_extensions'] == []

    def test_python_only_disables_md(self):
        assert presets_mod.preset_options('python_only')['include_md'] is False

    def test_web_assets_includes_md(self):
        assert presets_mod.preset_options('web_assets')['include_md'] is True

    def test_unknown_preset_is_empty(self):
        assert presets_mod.preset_options('nope') == {}

    def test_extra_list_is_copied(self):
        """Muter la valeur renvoyée ne doit pas corrompre le preset."""
        values = presets_mod.preset_options('full')
        values['extra_extensions'].append('.exe')
        assert '.exe' not in presets_mod.preset_options('full')['extra_extensions']

    def test_all_extra_are_whitelisted(self):
        for ext in presets_mod.ALL_EXTRA_EXTENSIONS:
            assert ext in ALLOWED_EXTRA_EXTENSIONS

    def test_full_preset_survives_validation(self):
        """Le preset Complet doit passer la liste blanche du schéma."""
        values = presets_mod.preset_options('full')
        opts = ExtractionOptions(**{
            k: v for k, v in values.items() if k != 'include_file_metadata'
        })
        assert opts.extra_extensions == list(presets_mod.ALL_EXTRA_EXTENSIONS)


class TestApplyPresetToUI:
    """apply_preset() appliqué à une fausse UI."""

    def test_apply_full_checks_every_box(self):
        from src.gui.ui_builder.menus import apply_preset
        ui = _FakeUI()
        apply_preset(ui, 'full')
        for _attr, exts, _label in EXTRA_EXT_CHOICES:
            assert getattr(ui, _attr).get() is True
        assert collect_extra_extensions(ui) == list(presets_mod.ALL_EXTRA_EXTENSIONS)

    def test_apply_minimal_unchecks_every_box(self):
        from src.gui.ui_builder.menus import apply_preset
        ui = _FakeUI(**{a: True for a, _, _ in EXTRA_EXT_CHOICES})
        apply_preset(ui, 'minimal')
        for _attr, exts, _label in EXTRA_EXT_CHOICES:
            assert getattr(ui, _attr).get() is False
        assert collect_extra_extensions(ui) == []

    def test_apply_unknown_preset_is_noop(self):
        from src.gui.ui_builder.menus import apply_preset
        ui = _FakeUI(extra_ext_toml=True)
        apply_preset(ui, 'nope')
        assert ui.extra_ext_toml.get() is True


class TestYamlSupport:
    """Support YAML : liste blanche, case GUI, preset."""

    def test_yaml_extensions_are_whitelisted(self):
        """`.yaml` et `.yml` doivent être dans ALLOWED_EXTRA_EXTENSIONS."""
        assert '.yaml' in ALLOWED_EXTRA_EXTENSIONS
        assert '.yml' in ALLOWED_EXTRA_EXTENSIONS

    def test_yaml_box_declares_both_extensions(self):
        entry = next(c for c in EXTRA_EXT_CHOICES if c[0] == 'extra_ext_yaml')
        assert entry[1] == ('.yaml', '.yml')

    def test_yaml_box_collects_both_in_order(self):
        """Une seule case cochée doit produire les DEUX extensions, dans
        l'ordre .yaml puis .yml (ordre de la liste blanche)."""
        assert collect_extra_extensions(_FakeUI(extra_ext_yaml=True)) == ['.yaml', '.yml']

    def test_full_preset_includes_both_yaml_extensions(self):
        extras = presets_mod.preset_options('full')['extra_extensions']
        assert '.yaml' in extras
        assert '.yml' in extras

    def test_non_full_presets_exclude_yaml(self):
        for preset in ('python_only', 'web_assets', 'minimal'):
            extras = presets_mod.preset_options(preset)['extra_extensions']
            assert '.yaml' not in extras, preset
            assert '.yml' not in extras, preset

    def test_yaml_survives_schema_validation(self):
        """Les deux extensions traversent le validateur de liste blanche."""
        opts = ExtractionOptions(extra_extensions=['.yaml', '.yml', '.exe'])
        assert opts.extra_extensions == ['.yaml', '.yml']

    def test_file_type_labels_are_yaml(self):
        """Les deux extensions doivent produire le même type dans l'export."""
        from src.extractor.file_processor import file_type_for_ext
        assert file_type_for_ext('.yaml') == 'YAML'
        assert file_type_for_ext('.yml') == 'YAML'

    def test_only_whitelisted_box_is_checked(self):
        """cocher YAML ne doit pas révéler TOML ni XML."""
        ui = _FakeUI(extra_ext_yaml=True)
        assert collect_extra_extensions(ui) == ['.yaml', '.yml']
        assert ui.extra_ext_toml.get() is False
        assert ui.extra_ext_xml.get() is False

    def test_yaml_synonyms_share_one_stat_bucket(self):
        """.yaml et .yml doivent être COMPTÉS ensemble, sinon le rapport
        affiche deux lignes « Fichiers YAML » identiques."""
        from src.extractor.context import stat_key_for_ext
        assert stat_key_for_ext('.yaml') == 'yaml'
        assert stat_key_for_ext('.yml') == 'yaml'

    def test_report_has_single_yaml_line(self, tmp_path):
        """Un dossier avec ci.yml ET values.yaml → une seule ligne YAML."""
        from io import StringIO

        from src.config import ExtractionOptions as Opts
        from src.extractor.context import ExtractionContext
        from src.extractor.report_builder import ReportBuilder

        (tmp_path / "ci.yml").write_text("on: push\n", encoding='utf-8')
        (tmp_path / "values.yaml").write_text("version: 2\n", encoding='utf-8')

        ctx = ExtractionContext(
            folder_path=tmp_path,
            options=Opts(extra_extensions=['.yaml', '.yml']),
            output_path=tmp_path / "out.txt",
        )
        ctx.stats['yaml'] = 2
        ctx.line_counts['yaml'] = 2

        out = StringIO()
        ReportBuilder(ctx).write_statistics(out)
        report = out.getvalue()
        assert report.count("Fichiers YAML") == 1
        assert "Fichiers YAML                : 2" in report
        assert report.count("Nombre de lignes (YAML)") == 1


class TestGetAllowedExtensions:
    """get_allowed_extensions() (sélection de fichiers)."""

    def test_md_absent_by_default(self):
        assert '.md' not in get_allowed_extensions({})

    def test_md_present_when_enabled(self):
        assert '.md' in get_allowed_extensions({'include_md': True})

    def test_extras_appended(self):
        exts = get_allowed_extensions({'extra_extensions': ['.toml', '.yml']})
        assert '.toml' in exts and '.yml' in exts

    def test_extras_filtered_against_whitelist(self):
        exts = get_allowed_extensions({'extra_extensions': ['.toml', '.exe', '.dll']})
        assert '.toml' in exts
        assert '.exe' not in exts
        assert '.dll' not in exts

    def test_extras_normalized(self):
        assert '.yaml' in get_allowed_extensions({'extra_extensions': ['YAML', ' ini ']})

    def test_extras_not_duplicated(self):
        exts = get_allowed_extensions({'include_md': True,
                                       'extra_extensions': ['.md', '.toml']})
        assert exts.count('.md') == 1

    def test_garbage_extra_container_ignored(self):
        assert get_allowed_extensions({'extra_extensions': 'toml'}) is not None
        assert get_allowed_extensions({'extra_extensions': 42}) is not None
        assert get_allowed_extensions({'extra_extensions': None}) is not None

    def test_non_string_entries_ignored(self):
        exts = get_allowed_extensions({'extra_extensions': [None, 3, '.toml']})
        assert exts.count('.toml') == 1

    def test_accepts_extraction_options_object(self):
        opts = ExtractionOptions(include_md=True, extra_extensions=['.xml'])
        exts = get_allowed_extensions(opts)
        assert '.md' in exts and '.xml' in exts


class TestFolderScanner:
    """scan_folder() avec les nouvelles extensions."""

    def test_counts_md_and_extras(self, tmp_path):
        from src.gui.folder_scanner import scan_folder
        (tmp_path / "a.py").write_text("x = 1\n", encoding='utf-8')
        (tmp_path / "b.md").write_text("# b\n", encoding='utf-8')
        (tmp_path / "c.toml").write_text("[t]\n", encoding='utf-8')
        (tmp_path / "d.yml").write_text("k: v\n", encoding='utf-8')
        (tmp_path / "e.yaml").write_text("j: w\n", encoding='utf-8')

        stats = scan_folder(str(tmp_path), ExtractionOptions(
            include_md=True, extra_extensions=['.toml', '.yml', '.yaml']))
        assert stats['total'] == 5
        assert stats['types']['py'] == 1
        assert stats['types']['md'] == 1
        assert stats['types']['toml'] == 1
        # .yml et .yaml fusionnent (comme dans le rapport d'export)
        assert stats['types']['yaml'] == 2

    def test_md_absent_by_default(self, tmp_path):
        from src.gui.folder_scanner import scan_folder
        (tmp_path / "a.py").write_text("x = 1\n", encoding='utf-8')
        (tmp_path / "b.md").write_text("# b\n", encoding='utf-8')
        stats = scan_folder(str(tmp_path), ExtractionOptions())
        assert stats['types']['md'] == 0
        assert stats['total'] == 1


class TestApplyExtractionFlags:
    """apply_extraction_flags() : UI -> ExtractionOptions."""

    def test_writes_md_and_extras(self):
        from src.gui.ui_builder.ui_widgets import apply_extraction_flags
        ui = _FakeUI(include_md=True, extra_ext_toml=True, extra_ext_xml=True)
        opts = ExtractionOptions()
        apply_extraction_flags(ui, opts)
        assert opts.include_md is True
        assert opts.extra_extensions == ['.toml', '.xml']

    def test_missing_attributes_do_not_raise(self):
        from src.gui.ui_builder.ui_widgets import apply_extraction_flags
        opts = ExtractionOptions()
        apply_extraction_flags(types.SimpleNamespace(), opts)
        assert opts.extra_extensions == []


class TestConfigJson:
    """Cohérence du config.json livré avec le schéma."""

    @staticmethod
    def _repo_config():
        from pathlib import Path
        cfg = Path(__file__).resolve().parents[2] / "config.json"
        return json.loads(cfg.read_text(encoding='utf-8'))

    def test_has_include_md_false(self):
        extraction = self._repo_config()["extraction"]
        assert extraction["include_md"] is False

    def test_has_empty_extra_extensions(self):
        extraction = self._repo_config()["extraction"]
        assert extraction["extra_extensions"] == []

    def test_matches_schema_defaults(self):
        extraction = self._repo_config()["extraction"]
        defaults = ExtractionOptions().model_dump()
        for key in ("include_md", "extra_extensions"):
            assert extraction[key] == defaults[key], key

    def test_loads_through_schema(self):
        extraction = self._repo_config()["extraction"]
        opts = ExtractionOptions(**extraction)
        assert opts.include_md is False
        assert opts.extra_extensions == []


class TestExtensionsTabGui:
    """Onglet « Extensions avancées » (nécessite un display)."""

    def test_tab_collects_checkboxes(self, tk_frame):
        import tkinter as tk

        from src.gui.settings.tabs import ExtensionsTab
        from src.gui.ui_builder.ui_widgets import UIWidgets

        ui = UIWidgets()
        for attr, _exts, _label in EXTRA_EXT_CHOICES:
            setattr(ui, attr, tk.BooleanVar(value=False))

        class _Dialog:
            pass

        dialog = _Dialog()
        dialog.ui = ui
        dialog._original_options = {}

        tab = ExtensionsTab(tk_frame, dialog)
        assert tab.collect() == []

        ui.extra_ext_toml.set(True)
        ui.extra_ext_ini.set(True)
        assert tab.collect() == ['.toml', '.ini', '.cfg']

        # La case YAML couvre .yaml et .yml d'un seul geste
        ui.extra_ext_yaml.set(True)
        assert '.yaml' in tab.collect() and '.yml' in tab.collect()

        # Chaque case est enregistrée pour la détection de changement
        assert 'extra_ext_toml' in dialog._original_options

    def test_tab_renders_all_choices(self, tk_frame):
        import tkinter as tk
        from tkinter import ttk

        from src.gui.settings.tabs import ExtensionsTab
        from src.gui.ui_builder.ui_widgets import UIWidgets

        ui = UIWidgets()
        for attr, _exts, _label in EXTRA_EXT_CHOICES:
            setattr(ui, attr, tk.BooleanVar(value=False))

        class _Dialog:
            pass

        dialog = _Dialog()
        dialog.ui = ui
        dialog._original_options = {}

        frame = tk_frame
        ExtensionsTab(frame, dialog)
        checkbuttons = [
            w for w in frame.winfo_children() if isinstance(w, ttk.Checkbutton)
        ]
        assert len(checkbuttons) == len(EXTRA_EXT_CHOICES)

    def test_tab_without_ui_vars_shows_placeholder(self, tk_frame):
        """Sans cases (extraction headless), l'onglet ne lève pas."""
        from src.gui.settings.tabs import ExtensionsTab
        from src.gui.ui_builder.ui_widgets import UIWidgets

        class _Dialog:
            pass

        dialog = _Dialog()
        dialog.ui = UIWidgets()  # aucune case extra_ext_*
        dialog._original_options = {}

        tab = ExtensionsTab(tk_frame, dialog)
        assert tab.collect() == []

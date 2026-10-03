# tests/integration/test_extraction_pipeline.py
"""Tests d'intégration : pipeline complète extraction → parsing → reconstruction."""
from __future__ import annotations

from pathlib import Path

from src.tools.builder import (
    BuildPlan,
    ParsedFile,
    build_project,
    parse_log,
    sanitize_path,
    validate_log,
)


def _build_realistic_log() -> str:
    """Construit un journal T-E réaliste avec format 80 '=' séparateurs."""
    files = [
        ("python", "src/__init__.py", "", "src", "15 octets", 2),
        ("python", "src/main.py",
         "import sys\n\ndef main():\n    print('Hello')\n\nif __name__ == '__main__':\n    main()\n",
         "src", "200 octets", 7),
        ("json", "config.json",
         '{\n  "app_name": "my_app",\n  "version": "1.0"\n}\n',
         ".", "50 octets", 4),
        ("python", "src/utils.py",
         "def helper():\n    return 42\n",
         "src", "80 octets", 3),
    ]
    sep = "=" * 80
    dash = "-" * 80
    lines = [
        "Extraction du code du dossier : C:/Projects/my_app",
        "Date d'extraction : 2025-06-15",
        sep, "",
    ]
    for file_type, rel_path, content, parent, size, line_count in files:
        lines.extend([
            sep,
            "FICHIER %s : %s" % (file_type, rel_path),
            "Type: %s" % file_type,
            "Chemin complet: C:/Projects/my_app/%s" % rel_path,
            "Dossier parent: %s" % parent,
            "Taille: %s" % size,
            "Nombre de lignes: %d" % line_count,
            dash,
            content,
            "" if content.endswith("\n") else "",
            "--- FIN DU FICHIER ---",
            "",
        ])
    return "\n".join(lines)


class TestExtractionPipeline:
    """Tests de bout en bout : parsing → validation → reconstruction."""

    def test_roundtrip_parse_and_validate(self):
        """Un journal T-E peut être parsé et validé."""
        log = _build_realistic_log()
        valid, msg = validate_log(log)
        assert valid is True, f"Validation failed: {msg}"

        plan = parse_log(log)
        assert plan.original_folder == "C:/Projects/my_app"
        assert plan.extraction_date == "2025-06-15"
        assert plan.total_files == 4

    def test_roundtrip_reconstruct_files(self, tmp_path):
        """Les fichiers parsés peuvent être reconstruits sur disque."""
        log = _build_realistic_log()
        plan = parse_log(log)
        dest = tmp_path / "reconstructed"

        stats = build_project(
            plan, dest,
            skip_binary=True,
            skip_hidden=True,
            overwrite=True,
        )
        assert stats['created'] == 4
        assert stats['errors'] == 0
        assert (dest / "config.json").exists()
        assert (dest / "src" / "main.py").exists()

    def test_roundtrip_content_preserved(self, tmp_path):
        """Le contenu des fichiers est préservé après reconstruction."""
        log = _build_realistic_log()
        plan = parse_log(log)
        dest = tmp_path / "reconstructed"

        build_project(plan, dest, skip_binary=True, skip_hidden=True)

        main = (dest / "src" / "main.py").read_text(encoding="utf-8")
        assert "def main():" in main
        assert "print('Hello')" in main

        config = (dest / "config.json").read_text(encoding="utf-8")
        assert '"app_name"' in config
        assert '"my_app"' in config

    def test_roundtrip_with_selected_files(self, tmp_path):
        """Seuls les fichiers sélectionnés sont reconstruits."""
        log = _build_realistic_log()
        plan = parse_log(log)
        dest = tmp_path / "reconstructed"

        stats = build_project(
            plan, dest,
            selected_files=["src/main.py"],
            skip_binary=True,
            skip_hidden=True,
        )
        assert stats['created'] == 1
        assert (dest / "src" / "main.py").exists()
        assert not (dest / "config.json").exists()

    def test_roundtrip_dry_run(self, tmp_path):
        """Le dry-run simule sans écrire."""
        log = _build_realistic_log()
        plan = parse_log(log)
        dest = tmp_path / "reconstructed"

        stats = build_project(plan, dest, dry_run=True)
        assert stats['created'] == 4
        assert stats['dry_run'] is True
        assert not dest.exists()

    def test_roundtrip_preserves_path_structure(self, tmp_path):
        """La structure de dossiers est correctement reconstruite."""
        log = _build_realistic_log()
        plan = parse_log(log)
        dest = tmp_path / "reconstructed"

        build_project(plan, dest, skip_binary=True, skip_hidden=True)

        assert dest.is_dir()
        assert (dest / "src").is_dir()
        assert (dest / "src" / "__init__.py").is_file()
        assert (dest / "src" / "main.py").is_file()
        assert (dest / "src" / "utils.py").is_file()
        assert (dest / "config.json").is_file()


def _extract(tmp_path, **overrides):
    """Lance une extraction réelle sur un dossier temporaire.

    Retourne (texte_du_journal, stats_dict).
    """
    from src.config import ExtractionOptions
    from src.extractor.context import ExtractionContext
    from src.extractor.engine import ExtractionEngine

    opts = ExtractionOptions(include_structure=False, **overrides)
    out = tmp_path / "export.txt"
    ctx = ExtractionContext(
        folder_path=tmp_path / "src",
        options=opts,
        output_path=out,
    )
    engine = ExtractionEngine(ctx)
    assert engine.run() == 'success', "extraction échouée"
    return out.read_text(encoding='utf-8'), ctx.stats


def _write_project(root):
    """Crée un mini-projet contenant .py, .md, .toml, .yml et .yaml."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "main.py").write_text("print('hi')\n", encoding='utf-8')
    (root / "README.md").write_text("# Projet\n\nDocumentation.\n", encoding='utf-8')
    (root / "pyproject.toml").write_text(
        '[project]\nname = "demo"\n', encoding='utf-8')
    (root / "ci.yml").write_text("on: push\n", encoding='utf-8')
    (root / "values.yaml").write_text("version: 2\n", encoding='utf-8')
    return root


class TestExtractionNewExtensions:
    """Extraction bout en bout avec .md et extra_extensions."""

    def test_md_ignored_by_default(self, tmp_path):
        """include_md=False (défaut) : aucun .md dans le journal."""
        src = _write_project(tmp_path / "src")
        text, _stats = _extract(tmp_path)
        assert "README.md" not in text
        assert "Documentation." not in text
        assert "FICHIER Markdown" not in text
        assert "main.py" in text
        assert src.exists()

    def test_md_included_when_enabled(self, tmp_path):
        """include_md=True : section « FICHIER Markdown » + contenu."""
        _write_project(tmp_path / "src")
        text, stats = _extract(tmp_path, include_md=True)
        assert "FICHIER Markdown : README.md" in text
        assert "# Projet" in text
        assert "Fichiers Markdown (.md)      : 1" in text
        assert stats['md'] == 1

    def test_extra_extensions_included(self, tmp_path):
        """extra_extensions : .toml et .yml inclus, .md toujours exclu."""
        _write_project(tmp_path / "src")
        text, stats = _extract(
            tmp_path, extra_extensions=['.toml', '.yaml', '.yml'])
        assert "FICHIER TOML : pyproject.toml" in text
        assert "FICHIER YAML : ci.yml" in text
        assert 'name = "demo"' in text
        assert "FICHIER Markdown" not in text
        assert stats['toml'] == 1
        # .yml et .yaml partagent le compteur 'yaml' (synonymes fusionnés)
        assert stats['yaml'] == 2

    def test_extra_extensions_match_exactly(self, tmp_path):
        """`.yaml` n'inclut pas implicitement `.yml` : ce sont deux entrées
        distinctes de la liste blanche (l'onglet GUI coche les deux d'un
        seul geste, via EXTRA_EXT_CHOICES)."""
        _write_project(tmp_path / "src")
        text, stats = _extract(tmp_path, extra_extensions=['.yaml'])
        assert "ci.yml" not in text
        # .yaml est bien extrait, et lui seul
        assert "FICHIER YAML : values.yaml" in text
        assert stats['yaml'] == 1
        assert stats.get('yml', 0) == 0

    def test_extra_extensions_stats_and_totals(self, tmp_path):
        """Les compteurs supplémentaires alimentent le total du rapport."""
        _write_project(tmp_path / "src")
        text, stats = _extract(tmp_path, include_md=True,
                               extra_extensions=['.toml', '.yaml', '.yml'])
        # 1 .py + 1 .md + 1 .toml + 2 YAML (.yml + .yaml regroupés)
        assert "Nombre total de fichiers     : 5" in text
        assert "Autres extensions" in text
        assert "Fichiers TOML                : 1" in text
        assert "Fichiers YAML                : 2" in text
        assert "Nombre de lignes (TOML)      : 2" in text
        assert stats['py'] == 1
        assert stats['md'] == 1
        assert stats['yaml'] == 2

    def test_extra_extensions_reject_binary(self, tmp_path):
        """Un .exe listé dans extra_extensions reste exclu (liste blanche)."""
        src = _write_project(tmp_path / "src")
        (src / "payload.exe").write_bytes(b'MZ\x90\x00binary')
        text, _stats = _extract(
            tmp_path, extra_extensions=['.toml', '.exe'])
        assert "payload.exe" not in text
        assert "pyproject.toml" in text

    def test_reconstruction_roundtrip_with_new_types(self, tmp_path):
        """Le Builder reconstruit correctement .md et .toml depuis le log."""
        from src.tools.builder import build_project, parse_log, validate_log

        _write_project(tmp_path / "src")
        text, _stats = _extract(tmp_path, include_md=True,
                               extra_extensions=['.toml'])

        valid, msg = validate_log(text)
        assert valid is True, msg

        plan = parse_log(text)
        assert plan.total_files == 3
        assert {f.rel_path for f in plan.files} == {
            "main.py", "README.md", "pyproject.toml"}

        dest = tmp_path / "rebuilt"
        stats = build_project(plan, dest, skip_binary=True, skip_hidden=True)
        assert stats['created'] == 3
        assert (dest / "README.md").read_text(encoding='utf-8').startswith("# Projet")
        assert 'name = "demo"' in (dest / "pyproject.toml").read_text(encoding='utf-8')


class TestExtractionYaml:
    """Extraction bout en bout des deux extensions YAML."""

    def test_both_yaml_extensions_produce_two_sections(self, tmp_path):
        """extra_extensions=['.yaml', '.yml'] -> deux sections
        « FICHIER YAML : ... », une par fichier."""
        _write_project(tmp_path / "src")
        text, stats = _extract(
            tmp_path, extra_extensions=['.yaml', '.yml'])

        assert text.count("FICHIER YAML : ") == 2, text
        assert "FICHIER YAML : ci.yml" in text
        assert "FICHIER YAML : values.yaml" in text
        # .yml et .yaml sont regroupés dans un compteur unique
        assert stats['yaml'] == 2
        assert 'yml' not in stats

    def test_yaml_content_is_preserved_verbatim(self, tmp_path):
        """Le contenu YAML est recopié tel quel (jamais réinterprété)."""
        src = _write_project(tmp_path / "src")
        (src / "docker-compose.yaml").write_text(
            "services:\n  web:\n    image: nginx:alpine\n",
            encoding='utf-8')
        text, _stats = _extract(
            tmp_path, extra_extensions=['.yaml', '.yml'])

        assert "FICHIER YAML : docker-compose.yaml" in text
        assert "image: nginx:alpine" in text

    def test_yaml_stats_reported_under_other_extensions(self, tmp_path):
        """Les compteurs YAML apparaissent sous « Autres extensions »."""
        _write_project(tmp_path / "src")
        text, _stats = _extract(
            tmp_path, extra_extensions=['.yaml', '.yml'])

        assert "Autres extensions" in text
        assert "Fichiers YAML                : 2" in text
        assert "Nombre total de fichiers     : 3" in text  # .py + 2 YAML

    def test_yaml_ignored_without_extra_extensions(self, tmp_path):
        """Sans extra_extensions, aucun YAML n'est extrait (rétro-compat)."""
        _write_project(tmp_path / "src")
        text, stats = _extract(tmp_path)
        assert "FICHIER YAML" not in text
        assert "ci.yml" not in text
        assert "values.yaml" not in text
        assert stats.get('yaml', 0) == 0

    def test_yaml_roundtrip_through_builder(self, tmp_path):
        """Le Builder reconstruit les fichiers YAML depuis le journal."""
        from src.tools.builder import build_project, parse_log, validate_log

        _write_project(tmp_path / "src")
        text, _stats = _extract(
            tmp_path, extra_extensions=['.yaml', '.yml'])

        valid, msg = validate_log(text)
        assert valid is True, msg

        plan = parse_log(text)
        assert plan.total_files == 3
        assert {f.rel_path for f in plan.files} == {
            "main.py", "ci.yml", "values.yaml"}

        dest = tmp_path / "rebuilt"
        stats = build_project(plan, dest, skip_binary=True, skip_hidden=True)
        assert stats['created'] == 3
        assert (dest / "ci.yml").read_text(encoding='utf-8') == "on: push\n"
        assert (dest / "values.yaml").read_text(encoding='utf-8') == "version: 2\n"


def _make_log(lines):
    """Helper: join lines into a log string."""
    return "\n".join(lines)


class TestExtractionPipelineEdgeCases:
    """Cas limites de la pipeline."""

    def test_single_file_log(self):
        """Un journal avec un seul fichier fonctionne."""
        log = _make_log([
            "Extraction du code du dossier : /tmp/test",
            "Date d'extraction : 2025-01-01",
            "=" * 80,
            "",
            "=" * 80,
            "FICHIER python : hello.py",
            "Type: python",
            "Chemin complet: /tmp/test/hello.py",
            "-" * 80,
            "print('hello')",
            "",
            "--- FIN DU FICHIER ---",
        ])
        valid, _ = validate_log(log)
        assert valid
        plan = parse_log(log)
        assert plan.total_files == 1
        assert plan.files[0].rel_path == "hello.py"

    def test_log_with_nested_directories(self, tmp_path):
        """Les chemins imbriqués sont reconstruits correctement."""
        log = _make_log([
            "Extraction du code du dossier : /src",
            "Date d'extraction : 2025-03-01",
            "=" * 80,
            "",
            "=" * 80,
            "FICHIER python : src/pkg/sub/module.py",
            "Type: python",
            "Chemin complet: /src/src/pkg/sub/module.py",
            "Dossier parent: src/pkg/sub",
            "Taille: 200 octets",
            "Nombre de lignes: 5",
            "-" * 80,
            "# module code",
            "",
            "--- FIN DU FICHIER ---",
        ])
        plan = parse_log(log)
        dest = tmp_path / "out"
        build_project(plan, dest, skip_binary=False, skip_hidden=False)
        assert (dest / "src" / "pkg" / "sub" / "module.py").exists()

    def test_sanitization_removes_dotdot(self):
        """Les chemins avec '..' sont nettoyés."""
        result = sanitize_path("../escape/passwd")
        assert ".." not in result
        assert "escape" in result or "passwd" in result

    def test_parse_log_metadata_variations(self):
        """Supporte les variations de métadonnées."""
        log = _make_log([
            "Extraction du code du dossier : /app",
            "Date d'extraction : 2025-12-25",
            "=" * 80,
            "",
            "=" * 80,
            "FICHIER python : app.py",
            "Type: python",
            "Chemin complet: /app/app.py",
            "Dossier parent: .",
            "-" * 80,
            "import os",
            "",
            "--- FIN DU FICHIER ---",
        ])
        plan = parse_log(log)
        assert plan.total_files == 1
        f = plan.files[0]
        assert f.parent_dir == "."
        assert f.size_hint == ""
        assert f.line_count == 0

    def test_parse_multiple_file_types(self):
        """Parse correctement plusieurs types de fichiers."""
        log = _make_log([
            "Extraction du code du dossier : /app",
            "Date d'extraction : 2025-06-01",
            "=" * 80,
            "",
            "=" * 80,
            "FICHIER python : main.py",
            "Type: python",
            "Chemin complet: /app/main.py",
            "-" * 80,
            "print('hello')",
            "",
            "--- FIN DU FICHIER ---",
            "",
            "=" * 80,
            "FICHIER JSON : config.json",
            "Type: JSON",
            "Chemin complet: /app/config.json",
            "-" * 80,
            '{"key": "value"}',
            "",
            "--- FIN DU FICHIER ---",
            "",
            "=" * 80,
            "FICHIER CSS : style.css",
            "Type: CSS",
            "Chemin complet: /app/style.css",
            "-" * 80,
            "body { color: red; }",
            "",
            "--- FIN DU FICHIER ---",
        ])
        plan = parse_log(log)
        assert plan.total_files == 3
        types = {f.file_type for f in plan.files}
        assert "python" in types
        assert "JSON" in types
        assert "CSS" in types

    def test_build_plan_summary(self, tmp_path):
        """Le résumé du BuildPlan est correct."""
        log = _build_realistic_log()
        plan = parse_log(log)
        summary = plan.summary()
        assert summary['total'] == 4
        assert summary['original_folder'] == "C:/Projects/my_app"
        assert summary['extraction_date'] == "2025-06-15"

    def test_build_with_overwrite_false_conflict(self, tmp_path):
        """Un conflit est détecté quand overwrite=False et le fichier existe."""
        log = _build_realistic_log()
        plan = parse_log(log)
        dest = tmp_path / "out"
        dest.mkdir()
        (dest / "config.json").write_text("old", encoding="utf-8")

        stats = build_project(
            plan, dest,
            overwrite=False,
            skip_binary=True,
            skip_hidden=True,
        )
        assert stats['conflicts'] >= 1
        assert (dest / "config.json").read_text(encoding="utf-8") == "old"

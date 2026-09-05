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

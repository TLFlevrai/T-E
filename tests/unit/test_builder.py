# tests/unit/test_builder.py
"""Tests unitaires pour l'outil Builder."""
from __future__ import annotations

import json
from pathlib import Path

from src.tools.builder import (
    BINARY_EXTENSIONS,
    IGNORED_DIRS,
    BuildPlan,
    ParsedFile,
    build_project,
    parse_log,
    sanitize_path,
    undo_build,
    validate_log,
)


class TestSanitizePath:
    """Tests pour sanitize_path()."""

    def test_simple_path(self):
        result = sanitize_path("src/main.py")
        assert "src" in result and "main.py" in result

    def test_nested_path(self):
        result = sanitize_path("src/utils/helper.py")
        assert "src" in result and "utils" in result and "helper.py" in result

    def test_removes_dotdot(self):
        result = sanitize_path("src/../etc/passwd")
        assert ".." not in result
        assert "etc" in result

    def test_preserves_dotgit(self):
        result = sanitize_path(".git/config")
        assert ".git" in result and "config" in result

    def test_empty_path(self):
        assert sanitize_path("") == ""

    def test_slash_normalization(self):
        result = sanitize_path("src\\utils\\file.py")
        assert "/" in result

    def test_dangerous_chars(self):
        result = sanitize_path('src/file<>:"|?*.py')
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result

    def test_backslash_only(self):
        assert sanitize_path("") == ""


class TestValidateLog:
    """Tests pour validate_log()."""

    def test_valid_log(self):
        log = self._make_log([("python", "main.py", "print('hi')")])
        valid, msg = validate_log(log)
        assert valid is True
        assert msg == ""

    def test_empty_content(self):
        valid, msg = validate_log("")
        assert valid is False
        assert "vide" in msg.lower()

    def test_whitespace_only(self):
        valid, msg = validate_log("   \n  \n  ")
        assert valid is False

    def test_missing_header(self):
        log = "Some random text\n--- FIN DU FICHIER ---"
        valid, msg = validate_log(log)
        assert valid is False
        assert "En-tête" in msg or "dossier" in msg

    def test_missing_end_marker(self):
        log = "Extraction du code du dossier : /test\n" + "=" * 80
        valid, msg = validate_log(log)
        assert valid is False
        assert "fin" in msg.lower() or "FIN" in msg or "introuvable" in msg.lower()

    def test_no_sections(self):
        log = "Extraction du code du dossier : /test\n--- FIN DU FICHIER ---"
        valid, msg = validate_log(log)
        assert valid is False
        assert "section" in msg.lower()

    def _make_log(self, files):
        lines = [
            "Extraction du code du dossier : /test/project",
            "Date d'extraction : 2024-01-01",
            "=" * 80,
            "",
        ]
        for file_type, rel_path, content in files:
            lines.append("=" * 80)
            lines.append(f"FICHIER {file_type} : {rel_path}")
            lines.append(f"Type: {file_type}")
            lines.append(f"Chemin complet: /test/project/{rel_path}")
            lines.append(f"Dossier parent: {Path(rel_path).parent!s}")
            lines.append("Taille: 100 octets")
            lines.append("Nombre de lignes: 5")
            lines.append("-" * 80)
            lines.append(content)
            if not content.endswith("\n"):
                lines.append("")
            lines.append("--- FIN DU FICHIER ---")
            lines.append("")
        return "\n".join(lines)


class TestParseLog:
    """Tests pour parse_log()."""

    def _make_log(self, files, header=None):
        lines = [
            "Extraction du code du dossier : /test/project",
            "Date d'extraction : 2024-01-01",
            "=" * 80,
            "",
        ]
        if header:
            lines.insert(0, header)
        for file_type, rel_path, content in files:
            lines.append("=" * 80)
            lines.append(f"FICHIER {file_type} : {rel_path}")
            lines.append(f"Type: {file_type}")
            lines.append(f"Chemin complet: /test/project/{rel_path}")
            lines.append(f"Dossier parent: {Path(rel_path).parent!s}")
            lines.append("Taille: 100 octets")
            lines.append("Nombre de lignes: 5")
            lines.append("-" * 80)
            lines.append(content)
            if not content.endswith("\n"):
                lines.append("")
            lines.append("--- FIN DU FICHIER ---")
            lines.append("")
        return "\n".join(lines)

    def test_parse_single_file(self):
        log = self._make_log([("python", "main.py", "print('hello')\n")])
        plan = parse_log(log)
        assert plan.original_folder == "/test/project"
        assert plan.total_files == 1
        assert plan.files[0].rel_path == "main.py"
        assert "print('hello')" in plan.files[0].content

    def test_parse_multiple_files(self):
        log = self._make_log([
            ("python", "main.py", "print('hello')\n"),
            ("json", "config.json", '{"key": "value"}\n'),
            ("text", "README.md", "# README\n"),
        ])
        plan = parse_log(log)
        assert plan.total_files == 3
        paths = [f.rel_path for f in plan.files]
        assert "main.py" in paths
        assert "config.json" in paths
        assert "README.md" in paths

    def test_parse_preserves_content(self):
        content = "def hello():\n    return 'world'\n"
        log = self._make_log([("python", "hello.py", content)])
        plan = parse_log(log)
        assert plan.total_files == 1
        assert "def hello():" in plan.files[0].content

    def test_parse_extracts_metadata(self):
        log = self._make_log([("python", "main.py", "code\n")])
        plan = parse_log(log)
        f = plan.files[0]
        assert f.full_path == "/test/project/main.py"
        assert f.parent_dir == "."
        assert f.line_count == 5
        assert f.file_type == "python"

    def test_parse_extracts_date(self):
        log = self._make_log([("python", "main.py", "code\n")])
        plan = parse_log(log)
        assert plan.extraction_date == "2024-01-01"

    def test_parse_empty_log(self):
        log = "Extraction du code du dossier : /test\n"
        log += "=" * 80 + "\n"
        log += "Extraction du code du dossier : /test\n--- FIN DU FICHIER ---"
        plan = parse_log(log)
        assert plan.total_files == 0

    def test_parse_40_dashes_separator(self):
        """Test avec séparateur de 40 tirets au lieu de 80."""
        lines = [
            "Extraction du code du dossier : /test",
            "=" * 80,
            "",
            "=" * 80,
            "FICHIER python : main.py",
            "Type: python",
            "Chemin complet: /test/main.py",
            "Dossier parent: .",
            "Taille: 10 octets",
            "Nombre de lignes: 1",
            "-" * 40,
            "code here",
            "",
            "--- FIN DU FICHIER ---",
            "",
        ]
        log = "\n".join(lines)
        plan = parse_log(log)
        assert plan.total_files == 1
        assert "code here" in plan.files[0].content

    def test_parse_missing_metadata_fields(self):
        """Test sans métadonnées optionnelles (Taille, Nombre de lignes)."""
        lines = [
            "Extraction du code du dossier : /test",
            "=" * 80,
            "",
            "=" * 80,
            "FICHIER python : main.py",
            "Type: python",
            "Chemin complet: /test/main.py",
            "-" * 80,
            "code here",
            "",
            "--- FIN DU FICHIER ---",
            "",
        ]
        log = "\n".join(lines)
        plan = parse_log(log)
        assert plan.total_files == 1
        assert plan.files[0].size_hint == ""
        assert plan.files[0].line_count == 0


class TestParsedFile:
    """Tests pour ParsedFile."""

    def test_is_binary(self):
        f = ParsedFile("image.png", "/path/image.png", "image", "")
        assert f.is_binary is True

    def test_is_not_binary(self):
        f = ParsedFile("main.py", "/path/main.py", "python", "")
        assert f.is_binary is False

    def test_should_ignore_git(self):
        f = ParsedFile(".git/config", "/path/.git/config", "text", "")
        assert f.should_ignore is True

    def test_should_ignore_pycache(self):
        f = ParsedFile("__pycache__/module.pyc", "/path/__pycache__/module.pyc", "binary", "")
        assert f.should_ignore is True

    def test_should_ignore_binary_ext(self):
        f = ParsedFile("video.mp4", "/path/video.mp4", "video", "")
        assert f.should_ignore is True

    def test_should_not_ignore_normal_file(self):
        f = ParsedFile("src/main.py", "/path/src/main.py", "python", "")
        assert f.should_ignore is False

    def test_extension_property(self):
        f = ParsedFile("test.py", "/path/test.py", "python", "")
        assert f.extension == ".py"

    def test_extension_case_insensitive(self):
        f = ParsedFile("test.PY", "/path/test.PY", "python", "")
        assert f.extension == ".py"

    def test_size_bytes(self):
        content = "hello world"
        f = ParsedFile("test.txt", "/path/test.txt", "text", content)
        assert f.size_bytes == len(content.encode('utf-8'))

    def test_to_dict(self):
        f = ParsedFile("main.py", "/path/main.py", "python", "code",
                       parent_dir="src", size_hint="100 octets", line_count=5)
        d = f.to_dict()
        assert d['rel_path'] == "main.py"
        assert d['file_type'] == "python"
        assert d['parent_dir'] == "src"
        assert d['line_count'] == 5


class TestBuildPlan:
    """Tests pour BuildPlan."""

    def test_empty_plan(self):
        plan = BuildPlan()
        assert plan.total_files == 0
        s = plan.summary()
        assert s['total'] == 0

    def test_add_files(self):
        plan = BuildPlan()
        plan.add_file(ParsedFile("a.py", "/a.py", "python", ""))
        plan.add_file(ParsedFile("b.png", "/b.png", "image", ""))
        assert plan.total_files == 2
        assert plan.text_count == 1
        assert plan.binary_count == 1

    def test_ignored_dirs_count(self):
        plan = BuildPlan()
        plan.add_file(ParsedFile(".git/config", "/.git/config", "text", ""))
        assert plan.ignored_count == 1


class TestBuildProject:
    """Tests pour build_project()."""

    def _make_plan(self, files=None):
        plan = BuildPlan()
        if files is None:
            files = [
                ("python", "main.py", "print('hello')\n"),
                ("json", "config.json", '{"key": "value"}\n'),
            ]
        for ftype, path, content in files:
            plan.add_file(ParsedFile(path, f"/src/{path}", ftype, content))
        return plan

    def test_basic_build(self, tmp_path):
        plan = self._make_plan()
        dest = tmp_path / "out"
        stats = build_project(plan, dest, skip_binary=False, skip_hidden=False)
        assert stats['created'] == 2
        assert stats['errors'] == 0
        assert (dest / "main.py").exists()
        assert (dest / "config.json").exists()
        assert "print('hello')" in (dest / "main.py").read_text(encoding='utf-8')

    def test_dry_run(self, tmp_path):
        plan = self._make_plan()
        dest = tmp_path / "out"
        stats = build_project(plan, dest, dry_run=True)
        assert stats['created'] == 2
        assert not dest.exists()

    def test_skip_binary(self, tmp_path):
        plan = self._make_plan([
            ("python", "main.py", "code\n"),
            ("image", "logo.png", "binary"),
        ])
        dest = tmp_path / "out"
        stats = build_project(plan, dest, skip_binary=True, skip_hidden=False)
        assert stats['created'] == 1
        assert stats['skipped'] == 1

    def test_skip_hidden(self, tmp_path):
        plan = self._make_plan([
            ("python", "main.py", "code\n"),
            ("text", ".env/config", "secret\n"),
        ])
        dest = tmp_path / "out"
        stats = build_project(plan, dest, skip_binary=False, skip_hidden=True)
        assert stats['created'] == 1
        assert stats['skipped'] == 1

    def test_no_overwrite_conflict(self, tmp_path):
        plan = self._make_plan([("python", "main.py", "new code\n")])
        dest = tmp_path / "out"
        dest.mkdir()
        (dest / "main.py").write_text("old code")
        stats = build_project(plan, dest, overwrite=False, skip_binary=False, skip_hidden=False)
        assert stats['conflicts'] == 1
        assert "old code" in (dest / "main.py").read_text(encoding='utf-8')

    def test_overwrite_existing(self, tmp_path):
        plan = self._make_plan([("python", "main.py", "new code\n")])
        dest = tmp_path / "out"
        dest.mkdir()
        (dest / "main.py").write_text("old code")
        stats = build_project(plan, dest, overwrite=True, skip_binary=False, skip_hidden=False)
        assert stats['created'] == 1
        assert "new code" in (dest / "main.py").read_text(encoding='utf-8')

    def test_nested_dirs_created(self, tmp_path):
        plan = self._make_plan([("python", "src/utils/helper.py", "code\n")])
        dest = tmp_path / "out"
        stats = build_project(plan, dest, skip_binary=False, skip_hidden=False)
        assert stats['created'] == 1
        assert (dest / "src/utils/helper.py").exists()

    def test_progress_callback(self, tmp_path):
        plan = self._make_plan()
        calls = []

        def on_progress(cur, total, path):
            calls.append((cur, total, path))

        dest = tmp_path / "out"
        build_project(plan, dest, on_progress=on_progress, skip_binary=False, skip_hidden=False)
        assert len(calls) == 2
        assert calls[-1][0] == 2

    def test_log_callback(self, tmp_path):
        plan = self._make_plan()
        logs = []

        def on_log(msg, level='info'):
            logs.append(msg)

        dest = tmp_path / "out"
        build_project(plan, dest, on_log=on_log, skip_binary=False, skip_hidden=False)
        assert any("main.py" in m for m in logs)

    def test_selected_files_filter(self, tmp_path):
        plan = self._make_plan([
            ("python", "a.py", "a\n"),
            ("python", "b.py", "b\n"),
        ])
        dest = tmp_path / "out"
        stats = build_project(plan, dest, selected_files=["a.py"],
                              skip_binary=False, skip_hidden=False)
        assert stats['created'] == 1
        assert (dest / "a.py").exists()
        assert not (dest / "b.py").exists()

    def test_manifest_written(self, tmp_path):
        plan = self._make_plan()
        dest = tmp_path / "out"
        build_project(plan, dest, skip_binary=False, skip_hidden=False)
        assert (dest / ".builder_manifest.json").exists()

    def test_manifest_not_in_dry_run(self, tmp_path):
        plan = self._make_plan()
        dest = tmp_path / "out"
        build_project(plan, dest, dry_run=True)
        assert not dest.exists()


class TestUndoBuild:
    """Tests pour undo_build()."""

    def test_undo_with_manifest(self, tmp_path):
        dest = tmp_path / "out"
        dest.mkdir()
        manifest = {
            'version': 1,
            'files': ['main.py', 'config.json'],
        }
        (dest / ".builder_manifest.json").write_text(json.dumps(manifest))
        (dest / "main.py").write_text("code")
        (dest / "config.json").write_text("config")

        ok, msg = undo_build(dest)
        assert ok is True
        assert not (dest / "main.py").exists()
        assert not (dest / "config.json").exists()

    def test_undo_no_manifest(self, tmp_path):
        dest = tmp_path / "out"
        dest.mkdir()
        ok, msg = undo_build(dest)
        assert ok is False
        assert "manifest" in msg.lower() or "Aucun" in msg


class TestBinaryExtensions:
    """Vérifie que la liste des extensions binaires est bien définie."""

    def test_image_extensions(self):
        assert '.png' in BINARY_EXTENSIONS
        assert '.jpg' in BINARY_EXTENSIONS
        assert '.gif' in BINARY_EXTENSIONS

    def test_video_extensions(self):
        assert '.mp4' in BINARY_EXTENSIONS
        assert '.avi' in BINARY_EXTENSIONS

    def test_archive_extensions(self):
        assert '.zip' in BINARY_EXTENSIONS
        assert '.tar' in BINARY_EXTENSIONS

    def test_text_not_in_binary(self):
        assert '.py' not in BINARY_EXTENSIONS
        assert '.json' not in BINARY_EXTENSIONS
        assert '.md' not in BINARY_EXTENSIONS


class TestIgnoredDirs:
    """Vérifie que la liste des dossiers ignorés est bien définie."""

    def test_git_ignored(self):
        assert '.git' in IGNORED_DIRS

    def test_pycache_ignored(self):
        assert '__pycache__' in IGNORED_DIRS

    def test_node_modules_ignored(self):
        assert 'node_modules' in IGNORED_DIRS

    def test_venv_ignored(self):
        assert '.venv' in IGNORED_DIRS
        assert 'venv' in IGNORED_DIRS

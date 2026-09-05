# tests/unit/test_report_builder.py
"""Tests unitaires pour ReportBuilder."""
from __future__ import annotations

from io import StringIO
from pathlib import Path
from unittest.mock import patch

from src.config import ExtractionOptions
from src.extractor.context import ExtractionContext
from src.extractor.report_builder import ReportBuilder


def _make_context(tmp_path, **overrides) -> ExtractionContext:
    """Crée un ExtractionContext pour les tests."""
    opts = ExtractionOptions(**overrides)
    return ExtractionContext(
        folder_path=tmp_path / "src_folder",
        options=opts,
        output_path=tmp_path / "output.txt",
    )


class TestReportBuilderInit:
    """Tests d'initialisation de ReportBuilder."""

    def test_creates_with_context(self, tmp_path):
        ctx = _make_context(tmp_path)
        builder = ReportBuilder(ctx)
        assert builder.context is ctx

    def test_stores_context_reference(self, tmp_path):
        ctx = _make_context(tmp_path)
        builder = ReportBuilder(ctx)
        assert builder.context.folder_path == tmp_path / "src_folder"


class TestReportBuilderWriteStatistics:
    """Tests de write_statistics()."""

    def test_writes_statistics_section(self, tmp_path):
        ctx = _make_context(tmp_path)
        builder = ReportBuilder(ctx)
        out = StringIO()

        builder.write_statistics(out)

        output = out.getvalue()
        assert "STATISTIQUES" in output
        assert "Fichiers Python" in output
        assert "Fichiers JSON" in output
        assert "Volume total extrait" in output

    def test_writes_zero_counts_by_default(self, tmp_path):
        ctx = _make_context(tmp_path)
        builder = ReportBuilder(ctx)
        out = StringIO()

        builder.write_statistics(out)

        output = out.getvalue()
        assert "Fichiers Python (.py)        : 0" in output
        assert "Fichiers JSON (.json)        : 0" in output

    def test_writes_nonzero_counts(self, tmp_path):
        ctx = _make_context(tmp_path)
        ctx.stats['py'] = 5
        ctx.stats['json'] = 3
        ctx.line_counts['py'] = 120
        ctx.line_counts['json'] = 45
        ctx.total_size = 2048

        builder = ReportBuilder(ctx)
        out = StringIO()

        builder.write_statistics(out)

        output = out.getvalue()
        assert "Fichiers Python (.py)        : 5" in output
        assert "Fichiers JSON (.json)        : 3" in output
        assert "Nombre de lignes (Python)    : 120" in output
        assert "Nombre de lignes (JSON)      : 45" in output

    def test_writes_size_in_bytes(self, tmp_path):
        ctx = _make_context(tmp_path)
        ctx.total_size = 500
        builder = ReportBuilder(ctx)
        out = StringIO()

        builder.write_statistics(out)

        assert "octets" in out.getvalue()

    def test_writes_size_in_kb(self, tmp_path):
        ctx = _make_context(tmp_path)
        ctx.total_size = 2048
        builder = ReportBuilder(ctx)
        out = StringIO()

        builder.write_statistics(out)

        assert "Ko" in out.getvalue()

    def test_writes_size_in_mb(self, tmp_path):
        ctx = _make_context(tmp_path)
        ctx.total_size = 2 * 1024 * 1024
        builder = ReportBuilder(ctx)
        out = StringIO()

        builder.write_statistics(out)

        assert "Mo" in out.getvalue()

    def test_total_files_count(self, tmp_path):
        ctx = _make_context(tmp_path)
        ctx.stats['py'] = 2
        ctx.stats['json'] = 1
        ctx.stats['txt'] = 3
        builder = ReportBuilder(ctx)
        out = StringIO()

        builder.write_statistics(out)

        output = out.getvalue()
        assert "Nombre total de fichiers     : 6" in output

    def test_total_lines_count(self, tmp_path):
        ctx = _make_context(tmp_path)
        ctx.line_counts['py'] = 100
        ctx.line_counts['json'] = 20
        ctx.line_counts['txt'] = 30
        builder = ReportBuilder(ctx)
        out = StringIO()

        builder.write_statistics(out)

        output = out.getvalue()
        assert "Nombre de lignes (Python)    : 100" in output
        assert "Nombre de lignes (JSON)      : 20" in output
        assert "Nombre de lignes (Texte)     : 30" in output
        assert "Nombre total de lignes       : 150" in output

    def test_html_css_js_counts(self, tmp_path):
        ctx = _make_context(tmp_path)
        ctx.stats['html'] = 4
        ctx.stats['css'] = 2
        ctx.stats['js'] = 7
        builder = ReportBuilder(ctx)
        out = StringIO()

        builder.write_statistics(out)

        output = out.getvalue()
        assert "Fichiers HTML (.html/.htm)   : 4" in output
        assert "Fichiers CSS (.css)          : 2" in output
        assert "Fichiers JavaScript (.js)    : 7" in output

    def test_separator_line_present(self, tmp_path):
        ctx = _make_context(tmp_path)
        builder = ReportBuilder(ctx)
        out = StringIO()

        builder.write_statistics(out)

        output = out.getvalue()
        assert "=" * 80 in output

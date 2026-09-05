# tests/unit/test_extractor_context.py
"""Tests unitaires pour ExtractionContext."""
from __future__ import annotations

from pathlib import Path

from src.config import ExtractionOptions
from src.extractor.context import ExtractionContext


class TestExtractionContext:
    """Tests pour ExtractionContext."""

    def test_default_stats(self, tmp_path):
        ctx = ExtractionContext(
            folder_path=tmp_path,
            options=ExtractionOptions(),
            output_path=tmp_path / "out",
        )
        assert ctx.stats['py'] == 0
        assert ctx.stats['json'] == 0
        assert ctx.total_size == 0
        assert ctx.processed_files == 0

    def test_initial_line_counts(self, tmp_path):
        ctx = ExtractionContext(
            folder_path=tmp_path,
            options=ExtractionOptions(),
            output_path=tmp_path / "out",
        )
        for key in ctx.line_counts:
            assert ctx.line_counts[key] == 0

    def test_stores_folder_path(self, tmp_path):
        ctx = ExtractionContext(
            folder_path=tmp_path / "project",
            options=ExtractionOptions(),
            output_path=tmp_path / "out",
        )
        assert ctx.folder_path == tmp_path / "project"

    def test_stores_output_path(self, tmp_path):
        out = tmp_path / "export.txt"
        ctx = ExtractionContext(
            folder_path=tmp_path,
            options=ExtractionOptions(),
            output_path=out,
        )
        assert ctx.output_path == out

    def test_stores_options(self, tmp_path):
        opts = ExtractionOptions(include_json=False, include_txt=True)
        ctx = ExtractionContext(
            folder_path=tmp_path,
            options=opts,
            output_path=tmp_path / "out",
        )
        assert ctx.options.include_json is False
        assert ctx.options.include_txt is True

    def test_selected_files_none_by_default(self, tmp_path):
        ctx = ExtractionContext(
            folder_path=tmp_path,
            options=ExtractionOptions(),
            output_path=tmp_path / "out",
        )
        assert ctx.selected_files is None

    def test_selected_files_can_be_set(self, tmp_path):
        ctx = ExtractionContext(
            folder_path=tmp_path,
            options=ExtractionOptions(),
            output_path=tmp_path / "out",
            selected_files={"a.py", "b.py"},
        )
        assert ctx.selected_files == {"a.py", "b.py"}

    def test_stats_all_keys_initialized(self, tmp_path):
        ctx = ExtractionContext(
            folder_path=tmp_path,
            options=ExtractionOptions(),
            output_path=tmp_path / "out",
        )
        expected_keys = {'py', 'json', 'txt', 'po', 'mo', 'html', 'css', 'js'}
        assert set(ctx.stats.keys()) == expected_keys
        assert set(ctx.line_counts.keys()) == expected_keys

    def test_line_counts_all_keys_initialized(self, tmp_path):
        ctx = ExtractionContext(
            folder_path=tmp_path,
            options=ExtractionOptions(),
            output_path=tmp_path / "out",
        )
        for key in ['py', 'json', 'txt', 'po', 'mo', 'html', 'css', 'js']:
            assert key in ctx.line_counts
            assert ctx.line_counts[key] == 0

    def test_total_size_default_zero(self, tmp_path):
        ctx = ExtractionContext(
            folder_path=tmp_path,
            options=ExtractionOptions(),
            output_path=tmp_path / "out",
        )
        assert ctx.total_size == 0

    def test_processed_files_default_zero(self, tmp_path):
        ctx = ExtractionContext(
            folder_path=tmp_path,
            options=ExtractionOptions(),
            output_path=tmp_path / "out",
        )
        assert ctx.processed_files == 0

    def test_stats_are_mutable(self, tmp_path):
        ctx = ExtractionContext(
            folder_path=tmp_path,
            options=ExtractionOptions(),
            output_path=tmp_path / "out",
        )
        ctx.stats['py'] = 10
        ctx.line_counts['py'] = 50
        ctx.total_size = 1024
        ctx.processed_files = 3

        assert ctx.stats['py'] == 10
        assert ctx.line_counts['py'] == 50
        assert ctx.total_size == 1024
        assert ctx.processed_files == 3

    def test_multiple_instances_independent(self, tmp_path):
        ctx1 = ExtractionContext(
            folder_path=tmp_path / "a",
            options=ExtractionOptions(),
            output_path=tmp_path / "out1",
        )
        ctx2 = ExtractionContext(
            folder_path=tmp_path / "b",
            options=ExtractionOptions(),
            output_path=tmp_path / "out2",
        )
        ctx1.stats['py'] = 5
        assert ctx2.stats['py'] == 0

    def test_options_defaults(self, tmp_path):
        ctx = ExtractionContext(
            folder_path=tmp_path,
            options=ExtractionOptions(),
            output_path=tmp_path / "out",
        )
        assert ctx.options.include_json is True
        assert ctx.options.include_subdirs is True
        assert ctx.options.show_file_paths is True
        assert ctx.options.include_structure is True
        assert ctx.options.include_statistics is True

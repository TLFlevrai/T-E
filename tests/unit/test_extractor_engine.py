# tests/unit/test_extractor_engine.py
"""Tests unitaires pour ExtractionEngine."""
from __future__ import annotations

import threading
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.config import ExtractionOptions
from src.extractor.context import ExtractionContext
from src.extractor.engine import (
    CANCELLED,
    FAILED,
    SUCCESS,
    ExtractionEngine,
)


def _make_context(tmp_path, **overrides) -> ExtractionContext:
    """Crée un ExtractionContext pour les tests."""
    opts = ExtractionOptions(
        include_structure=False,
        include_statistics=False,
        **overrides,
    )
    return ExtractionContext(
        folder_path=tmp_path / "src_folder",
        options=opts,
        output_path=tmp_path / "output.txt",
    )


class TestExtractionEngineInit:
    """Tests d'initialisation de l'engine."""

    def test_engine_creates_with_context(self, tmp_path):
        ctx = _make_context(tmp_path)
        engine = ExtractionEngine(ctx)
        assert engine.context is ctx
        assert engine.cancel_event is None

    def test_engine_discovery_uses_options(self, tmp_path):
        ctx = _make_context(tmp_path, ignore_pycache=True)
        engine = ExtractionEngine(ctx)
        assert engine.discovery is not None
        assert engine.processor is not None
        assert engine.report_builder is not None

    def test_set_cancel_event(self, tmp_path):
        ctx = _make_context(tmp_path)
        engine = ExtractionEngine(ctx)
        event = threading.Event()
        engine.set_cancel_event(event)
        assert engine.cancel_event is event


class TestExtractionEngineRun:
    """Tests de la méthode run() avec mocks."""

    def test_run_returns_failed_when_no_files(self, tmp_path):
        ctx = _make_context(tmp_path)
        ctx.folder_path.mkdir(parents=True, exist_ok=True)
        engine = ExtractionEngine(ctx)

        # Mock discovery to return empty list
        engine.discovery.find_files = MagicMock(return_value=[])
        result = engine.run()
        assert result == FAILED

    def test_run_returns_failed_when_no_files_and_log_callback(self, tmp_path):
        ctx = _make_context(tmp_path)
        ctx.folder_path.mkdir(parents=True, exist_ok=True)
        engine = ExtractionEngine(ctx)
        engine.discovery.find_files = MagicMock(return_value=[])

        logs = []
        result = engine.run(log_callback=lambda msg: logs.append(msg))
        assert result == FAILED
        assert any("Aucun fichier" in m for m in logs)

    def test_run_returns_success(self, tmp_path):
        ctx = _make_context(tmp_path)
        ctx.folder_path.mkdir(parents=True, exist_ok=True)
        engine = ExtractionEngine(ctx)

        # Mock discovery to return one file
        test_file = ctx.folder_path / "main.py"
        test_file.write_text("print('hi')\n", encoding="utf-8")

        engine.discovery.find_files = MagicMock(
            return_value=[(test_file, Path("main.py"), ".py")]
        )

        # Mock processor
        mock_result = MagicMock()
        mock_result.read_ok = True
        mock_result.file_type = "python"
        mock_result.rel_path = Path("main.py")
        mock_result.full_path = test_file
        mock_result.ext = ".py"
        mock_result.content = "print('hi')\n"
        mock_result.num_lines = 1
        mock_result.file_size = 12
        mock_result.show_file_paths = True
        mock_result.include_file_metadata = False
        engine.processor.process = MagicMock(return_value=mock_result)

        result = engine.run()
        assert result == SUCCESS

    def test_run_writes_output_file(self, tmp_path):
        ctx = _make_context(tmp_path)
        ctx.folder_path.mkdir(parents=True, exist_ok=True)
        engine = ExtractionEngine(ctx)

        test_file = ctx.folder_path / "main.py"
        test_file.write_text("code\n", encoding="utf-8")
        engine.discovery.find_files = MagicMock(
            return_value=[(test_file, Path("main.py"), ".py")]
        )

        mock_result = MagicMock()
        mock_result.read_ok = True
        mock_result.file_type = "python"
        mock_result.rel_path = Path("main.py")
        mock_result.full_path = test_file
        mock_result.ext = ".py"
        mock_result.content = "code\n"
        mock_result.num_lines = 1
        mock_result.file_size = 5
        mock_result.show_file_paths = True
        mock_result.include_file_metadata = False
        engine.processor.process = MagicMock(return_value=mock_result)

        engine.run()
        assert ctx.output_path.exists()
        content = ctx.output_path.read_text(encoding="utf-8")
        assert "Extraction du code du dossier" in content

    def test_run_calls_progress_callback(self, tmp_path):
        ctx = _make_context(tmp_path)
        ctx.folder_path.mkdir(parents=True, exist_ok=True)
        engine = ExtractionEngine(ctx)

        test_file = ctx.folder_path / "a.py"
        test_file.write_text("x=1\n", encoding="utf-8")
        engine.discovery.find_files = MagicMock(
            return_value=[(test_file, Path("a.py"), ".py")]
        )

        mock_result = MagicMock()
        mock_result.read_ok = True
        mock_result.file_type = "python"
        mock_result.rel_path = Path("a.py")
        mock_result.full_path = test_file
        mock_result.ext = ".py"
        mock_result.content = "x=1\n"
        mock_result.num_lines = 1
        mock_result.file_size = 4
        mock_result.show_file_paths = True
        mock_result.include_file_metadata = False
        engine.processor.process = MagicMock(return_value=mock_result)

        calls = []
        engine.run(progress_callback=lambda cur, total, path: calls.append((cur, total, path)))
        assert len(calls) == 1
        assert calls[0] == (1, 1, "a.py")


class TestExtractionEngineCancellation:
    """Tests d'annulation."""

    def test_cancel_event_stops_extraction(self, tmp_path):
        ctx = _make_context(tmp_path)
        ctx.folder_path.mkdir(parents=True, exist_ok=True)
        engine = ExtractionEngine(ctx)

        files = []
        for i in range(3):
            f = ctx.folder_path / f"file{i}.py"
            f.write_text(f"code{i}\n", encoding="utf-8")
            files.append((f, Path(f"file{i}.py"), ".py"))

        engine.discovery.find_files = MagicMock(return_value=files)

        # Pre-process results
        mock_results = []
        for i in range(3):
            r = MagicMock()
            r.read_ok = True
            r.file_type = "python"
            r.rel_path = Path(f"file{i}.py")
            r.full_path = files[i][0]
            r.ext = ".py"
            r.content = f"code{i}\n"
            r.num_lines = 1
            r.file_size = 6
            r.show_file_paths = True
            r.include_file_metadata = False
            mock_results.append(r)

        call_count = [0]

        def mock_process(full, rel, ext):
            idx = call_count[0]
            call_count[0] += 1
            if idx == 1:
                cancel_event.set()
            return mock_results[idx]

        engine.processor.process = mock_process

        cancel_event = threading.Event()
        engine.set_cancel_event(cancel_event)

        result = engine.run()
        assert result == CANCELLED

    def test_cancel_event_not_set_runs_all(self, tmp_path):
        ctx = _make_context(tmp_path)
        ctx.folder_path.mkdir(parents=True, exist_ok=True)
        engine = ExtractionEngine(ctx)

        files = []
        for i in range(2):
            f = ctx.folder_path / f"file{i}.py"
            f.write_text(f"code{i}\n", encoding="utf-8")
            files.append((f, Path(f"file{i}.py"), ".py"))

        engine.discovery.find_files = MagicMock(return_value=files)

        mock_results = []
        for i in range(2):
            r = MagicMock()
            r.read_ok = True
            r.file_type = "python"
            r.rel_path = Path(f"file{i}.py")
            r.full_path = files[i][0]
            r.ext = ".py"
            r.content = f"code{i}\n"
            r.num_lines = 1
            r.file_size = 6
            r.show_file_paths = True
            r.include_file_metadata = False
            mock_results.append(r)

        engine.processor.process = lambda full, rel, ext: mock_results.pop(0)

        cancel_event = threading.Event()
        engine.set_cancel_event(cancel_event)
        # Never set the event

        result = engine.run()
        assert result == SUCCESS


class TestExtractionEngineFilter:
    """Tests du filtrage sélection."""

    def test_filter_selected_files(self, tmp_path):
        ctx = _make_context(tmp_path)
        ctx.selected_files = {"main.py"}
        ctx.folder_path.mkdir(parents=True, exist_ok=True)
        engine = ExtractionEngine(ctx)

        all_files = [
            (Path("main.py"), Path("main.py"), ".py"),
            (Path("utils.py"), Path("utils.py"), ".py"),
        ]

        result = engine._filter_selected(all_files, None)
        assert len(result) == 1
        assert result[0][1].as_posix() == "main.py"

    def test_filter_selected_none_returns_all(self, tmp_path):
        ctx = _make_context(tmp_path)
        ctx.folder_path.mkdir(parents=True, exist_ok=True)
        engine = ExtractionEngine(ctx)

        all_files = [
            (Path("main.py"), Path("main.py"), ".py"),
        ]

        result = engine._filter_selected(all_files, None)
        assert result == all_files

    def test_filter_selected_empty_returns_none(self, tmp_path):
        ctx = _make_context(tmp_path)
        ctx.selected_files = {"nonexistent.py"}
        ctx.folder_path.mkdir(parents=True, exist_ok=True)
        engine = ExtractionEngine(ctx)

        all_files = [
            (Path("main.py"), Path("main.py"), ".py"),
        ]

        result = engine._filter_selected(all_files, None)
        assert result is None

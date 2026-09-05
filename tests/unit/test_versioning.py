# tests/unit/test_versioning.py
"""Tests unitaires pour le gestionnaire de versions."""
from __future__ import annotations

import threading
from pathlib import Path

from src.versioning import VersionManager


class TestVersionManager:
    """Tests pour VersionManager."""

    def test_get_next_version_first(self, tmp_path):
        vm = VersionManager(str(tmp_path / "versions.txt"))
        version = vm.get_next_version("project", str(tmp_path))
        assert version == 1

    def test_get_next_version_increment(self, tmp_path):
        vm = VersionManager(str(tmp_path / "versions.txt"))
        vm.use_version("project", 3)
        version = vm.get_next_version("project", str(tmp_path))
        assert version == 4

    def test_use_version(self, tmp_path):
        vm = VersionManager(str(tmp_path / "versions.txt"))
        vm.use_version("project", 5)
        assert vm.mapping["project"] == 5

    def test_save_and_load(self, tmp_path):
        version_file = tmp_path / "versions.txt"
        vm1 = VersionManager(str(version_file))
        vm1.use_version("project", 3)
        vm1.save_mapping()

        vm2 = VersionManager(str(version_file))
        assert vm2.mapping["project"] == 3

    def test_reset(self, tmp_path):
        version_file = tmp_path / "versions.txt"
        vm = VersionManager(str(version_file))
        vm.use_version("project", 5)
        vm.reset()
        assert vm.mapping == {}

    def test_reset_project(self, tmp_path):
        vm = VersionManager(str(tmp_path / "versions.txt"))
        vm.use_version("a", 1)
        vm.use_version("b", 2)
        vm.reset_project("a")
        assert "a" not in vm.mapping
        assert vm.mapping["b"] == 2

    def test_thread_safety(self, tmp_path):
        vm = VersionManager(str(tmp_path / "versions.txt"))
        errors = []

        def worker():
            try:
                for _ in range(50):
                    vm.get_next_version("project", str(tmp_path))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []

    def test_load_nonexistent_file(self, tmp_path):
        vm = VersionManager(str(tmp_path / "nonexistent.txt"))
        assert vm.mapping == {}

    def test_load_corrupted_file(self, tmp_path):
        version_file = tmp_path / "corrupted.txt"
        version_file.write_text("not:valid:corrupted\n", encoding='utf-8')
        vm = VersionManager(str(version_file))
        assert vm.mapping == {}

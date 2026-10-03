# tests/integration/test_archive_custom_output.py
"""Lot 1.4 : l'archivage des anciennes versions suit le dossier de sortie.

Quand l'utilisateur choisit un dossier de sortie personnalisé, les
anciennes versions doivent être archivées dans <custom>/out/old_out/,
pas dans le dossier de sortie par défaut de la configuration.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from src.services.extraction_service import ExtractionService


class _StubVersionManager:
    """VersionManager en mémoire : pas de fichier, pas de sentinel."""

    def __init__(self):
        self.reserved: dict[str, int] = {}

    def reserve_version(self, folder_name, output_dir="."):
        version = self.reserved.get(folder_name, 0) + 1
        self.reserved[folder_name] = version
        return version

    def release_version(self, folder_name, version, output_dir="."):
        pass

    def use_version(self, folder_name, version):
        pass

    def reset(self):
        self.reserved.clear()


class _StubConfig:
    """Config minimale pour VersionArchiveService (test hermétique)."""

    def __init__(self, values: dict):
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)


def _make_service(tmp_path: Path):
    """Service avec dossier de sortie par défaut + stubs hermétiques."""
    # Une extraction réelle appelle get_config().save() (modèle global) :
    # reset du singleton pour partir d'une config vierge.
    from src.config import _Config
    _Config._reset_for_testing()
    default_out = tmp_path / "default_out"
    custom_root = tmp_path / "custom"
    stub_cfg = _StubConfig({
        'output_dir': str(default_out),
        'archive_subdir': 'old_out',
        'version_file': str(tmp_path / "versions.txt"),
    })
    service = ExtractionService(
        extractor=object(),  # inutilisé : le service pilote ExtractionEngine
        version_manager=_StubVersionManager(),
        output_dir=default_out,
    )
    return service, default_out, custom_root, stub_cfg


def _write_source_project(root: Path) -> Path:
    src = root / "monprojet"
    src.mkdir(parents=True, exist_ok=True)
    (src / "main.py").write_text("print('ok')\n", encoding="utf-8")
    return src


class TestArchiveWithCustomOutputDir:

    def test_archive_targets_custom_dir(self, tmp_path):
        """archive_old=True + output_dir custom : v1 est archivée dans
        <custom>/out/old_out/monprojet/, jamais dans le dossier par défaut.

        Convention <output_dir_effectif>/old_out/<projet>/ : identique au
        cas par défaut (out/old_out/) et à clean_versions(archive=True).
        """
        service, default_out, custom_root, stub_cfg = _make_service(tmp_path)
        src = _write_source_project(tmp_path)
        custom_out = custom_root / "out"

        with patch("src.services.version_service.get_config",
                   return_value=stub_cfg):
            # Extraction n°1 : crée monprojetv1.txt dans <custom>/out
            ok1, out1, _stats = service.extract_folder(
                src, {'archive_old': False}, output_dir=custom_root)
            assert ok1 is True
            assert Path(out1).parent == custom_out
            assert (custom_out / "monprojetv1.txt").exists()

            # Extraction n°2 avec archivage : v1 doit partir dans l'archive
            ok2, out2, _stats = service.extract_folder(
                src, {'archive_old': True}, output_dir=custom_root)
            assert ok2 is True

        archive_dir = custom_out / "old_out" / "monprojet"
        assert archive_dir.is_dir(), f"archive absente : {archive_dir}"
        assert (archive_dir / "monprojetv1.txt").exists()
        # La nouvelle version reste active dans <custom>/out
        assert (custom_out / "monprojetv2.txt").exists()
        # Aucune fuite vers le dossier de sortie par défaut
        assert not (default_out / "old_out").exists()
        assert not list(default_out.rglob("monprojet*"))

    def test_archive_without_custom_dir_uses_default(self, tmp_path):
        """Sans output_dir custom : comportement historique (archive dans
        le dossier de sortie par défaut) est préservé."""
        service, default_out, _custom, stub_cfg = _make_service(tmp_path)
        src = _write_source_project(tmp_path)

        with patch("src.services.version_service.get_config",
                   return_value=stub_cfg):
            ok1, _out1, _s = service.extract_folder(src, {'archive_old': False})
            assert ok1 is True
            ok2, _out2, _s = service.extract_folder(src, {'archive_old': True})
            assert ok2 is True

        archive_dir = default_out / "old_out" / "monprojet"
        assert (archive_dir / "monprojetv1.txt").exists()
        assert (default_out / "monprojetv2.txt").exists()

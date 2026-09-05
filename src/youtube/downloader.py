# src/youtube/downloader.py
"""Téléchargement de vidéos et d'audio YouTube.

Gère le téléchargement avec progression, la fusion vidéo+audio via ffmpeg,
et la conversion audio en MP3 lorsque ffmpeg est disponible.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

from .exceptions import NetworkError
from .extractor import VideoInfo, extract_video_info, select_audio_stream, select_video_stream

# Callback type: (downloaded_bytes, total_bytes, speed_bytes_per_sec)
ProgressCallback = Callable[[int, int, int], None]


_MAX_FILENAME_LENGTH = 200


def _sanitize_filename(name: str) -> str:
    """Nettoie un nom de fichier pour éviter les caractères dangereux."""
    # Supprimer les caractères interdits sur Windows
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Limiter la longueur
    name = name.strip('. ')
    if len(name) > _MAX_FILENAME_LENGTH:
        name = name[:_MAX_FILENAME_LENGTH]
    return name or "video"


def _check_ffmpeg() -> bool:
    """Vérifie si ffmpeg est disponible dans le PATH."""
    return shutil.which("ffmpeg") is not None


def _download_stream(
    url: str,
    dest: Path,
    progress_cb: ProgressCallback | None = None,
    timeout: int = 60,
) -> int:
    """Télécharge un flux depuis une URL vers un fichier.

    Args:
        url: URL du flux à télécharger.
        dest: Chemin du fichier de sortie.
        progress_cb: Callback de progression (downloaded, total, speed).
        timeout: Timeout de connexion en secondes.

    Returns:
        La taille totale téléchargée en octets.

    Raises:
        NetworkError: En cas d'erreur réseau.
    """
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "*/*",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        },
    )

    try:
        response = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as exc:
        raise NetworkError(
            f"Erreur HTTP {exc.code} lors du téléchargement."
        ) from exc
    except urllib.error.URLError as exc:
        raise NetworkError(
            f"Erreur de connexion : {exc.reason}"
        ) from exc

    total_size = int(response.headers.get("Content-Length", 0) or 0)
    downloaded = 0
    chunk_size = 64 * 1024  # 64 Ko

    try:
        with dest.open("wb") as f:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if progress_cb:
                    progress_cb(downloaded, total_size, 0)
    except OSError as exc:
        raise NetworkError(f"Erreur d'écriture sur disque : {exc}") from exc

    return downloaded


def _get_video_title(info: VideoInfo) -> str:
    """Retourne le titre nettoyé de la vidéo."""
    return _sanitize_filename(info.title)


def _ffmpeg_merge(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
) -> bool:
    """Fusionne un flux vidéo et un flux audio avec ffmpeg."""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-c:a", "aac",
        "-strict", "experimental",
        str(output_path),
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=300,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False
    else:
        return result.returncode == 0


def _ffmpeg_to_mp3(
    input_path: Path,
    output_path: Path,
    quality: str = "192",
) -> bool:
    """Convertit un fichier audio/vidéo en MP3 avec ffmpeg."""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vn",
        "-acodec", "libmp3lame",
        "-ab", f"{quality}k",
        str(output_path),
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=300,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False
    else:
        return result.returncode == 0


def download_video(
    url: str,
    output_dir: str | Path,
    max_height: int = 360,
    progress_cb: ProgressCallback | None = None,
) -> Path:
    """Télécharge une vidéo YouTube en qualité ≤ max_height.

    Si ffmpeg est disponible et que les flux vidéo et audio sont séparés,
    ils sont fusionnés en un seul fichier MP4.

    Args:
        url: URL YouTube de la vidéo.
        output_dir: Répertoire de sortie.
        max_height: Hauteur maximale en pixels (défaut : 360).
        progress_cb: Callback de progression.

    Returns:
        Le chemin du fichier téléchargé.

    Raises:
        InvalidYouTubeURLError: URL invalide.
        VideoUnavailableError: Vidéo non disponible.
        FormatUnavailableError: Format non disponible.
        NetworkError: Erreur réseau.
    """
    info = extract_video_info(url)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    video_stream = select_video_stream(info, max_height=max_height)

    title = _get_video_title(info)
    has_ffmpeg = _check_ffmpeg()

    # Vérifier si le flux contient déjà l'audio (flux muxé)
    has_audio = video_stream.audio_quality != "" or "audio" in video_stream.mime_type.lower()

    if has_audio or not has_ffmpeg:
        # Flux muxé ou pas de ffmpeg : télécharger directement
        ext = video_stream.container
        output_path = output_dir / f"{title}.{ext}"

        def _progress(downloaded: int, total: int, speed: int) -> None:
            if progress_cb:
                progress_cb(downloaded, total, speed)

        _download_stream(video_stream.url, output_path, progress_cb=_progress)
        return output_path

    # Flux adaptatif : vidéo seule → chercher audio séparément
    audio_stream = select_audio_stream(info)

    with tempfile.TemporaryDirectory(prefix="yt_dl_") as tmpdir:
        tmp = Path(tmpdir)
        video_file = tmp / f"video.{video_stream.container}"
        audio_file = tmp / f"audio.{audio_stream.container}"
        merged_file = tmp / f"merged.{title}.mp4"

        # Télécharger la vidéo
        _download_stream(video_stream.url, video_file, progress_cb=progress_cb)

        # Télécharger l'audio
        _download_stream(audio_stream.url, audio_file, progress_cb=None)

        # Fusionner
        success = _ffmpeg_merge(video_file, audio_file, merged_file)

        if success and merged_file.exists():
            final_path = output_dir / f"{title}.mp4"
            shutil.move(str(merged_file), str(final_path))
            return final_path

        # Échec de la fusion : sauvegarder la vidéo seule
        fallback_path = output_dir / f"{title}.{video_stream.container}"
        shutil.move(str(video_file), str(fallback_path))
        return fallback_path


def download_audio(
    url: str,
    output_dir: str | Path,
    convert_mp3: bool = True,
    mp3_quality: str = "192",
    progress_cb: ProgressCallback | None = None,
) -> Path:
    """Télécharge l'audio d'une vidéo YouTube.

    Si ffmpeg est disponible et convert_mp3 est True, convertit en MP3.
    Sinon, télécharge le flux audio brut (m4a/webm).

    Args:
        url: URL YouTube de la vidéo.
        output_dir: Répertoire de sortie.
        convert_mp3: Convertir en MP3 si ffmpeg est disponible.
        mp3_quality: Qualité MP3 en kbps (défaut : 192).
        progress_cb: Callback de progression.

    Returns:
        Le chemin du fichier téléchargé.

    Raises:
        InvalidYouTubeURLError: URL invalide.
        VideoUnavailableError: Vidéo non disponible.
        FormatUnavailableError: Format non disponible.
        NetworkError: Erreur réseau.
    """
    info = extract_video_info(url)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    audio_stream = select_audio_stream(info)

    title = _get_video_title(info)
    has_ffmpeg = _check_ffmpeg()

    # Télécharger le flux audio brut
    ext = audio_stream.container
    raw_path = output_dir / f"{title}.{ext}"

    _download_stream(audio_stream.url, raw_path, progress_cb=progress_cb)

    if convert_mp3 and has_ffmpeg:
        mp3_path = output_dir / f"{title}.mp3"
        success = _ffmpeg_to_mp3(raw_path, mp3_path, quality=mp3_quality)
        if success and mp3_path.exists():
            raw_path.unlink(missing_ok=True)
            return mp3_path

    return raw_path

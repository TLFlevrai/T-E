# src/youtube/__init__.py
"""Module YouTube : téléchargement de vidéos et d'audio YouTube.

Fournit une API simple pour télécharger des vidéos en 360p maximum
et de l'audio depuis YouTube, sans dépendance à yt-dlp.

Exemple d'utilisation::

    from src.youtube import download_video, download_audio

    # Télécharger une vidéo en 360p
    path = download_video(
        url="https://www.youtube.com/watch?v=abc123",
        output_dir="./downloads",
    )

    # Télécharger l'audio en MP3
    path = download_audio(
        url="https://www.youtube.com/watch?v=abc123",
        output_dir="./downloads",
        convert_mp3=True,
    )
"""
from __future__ import annotations
from .downloader import download_audio, download_video
from .exceptions import (
    ExtractionError,
    FormatUnavailableError,
    InvalidYouTubeURLError,
    NetworkError,
    VideoUnavailableError,
    YouTubeError,
)
from .extractor import VideoInfo, extract_video_info, validate_url

__all__ = [
    "ExtractionError",
    "FormatUnavailableError",
    "InvalidYouTubeURLError",
    "NetworkError",
    "VideoInfo",
    "VideoUnavailableError",
    "YouTubeError",
    "download_audio",
    "download_video",
    "extract_video_info",
    "validate_url",
]
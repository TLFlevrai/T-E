# src/youtube/exceptions.py
"""Exceptions spécifiques au module YouTube."""
from __future__ import annotations


class YouTubeError(Exception):
    """Exception de base pour les erreurs YouTube."""


class InvalidYouTubeURLError(YouTubeError):
    """L'URL fournie n'est pas une URL YouTube valide."""


class VideoUnavailableError(YouTubeError):
    """La vidéo demandée n'est pas disponible (privée, supprimée, restreinte)."""


class FormatUnavailableError(YouTubeError):
    """Le format demandé n'est pas disponible pour cette vidéo."""


class NetworkError(YouTubeError):
    """Erreur réseau lors du téléchargement ou de l'extraction."""


class ExtractionError(YouTubeError):
    """Erreur lors de l'extraction des informations de la vidéo."""

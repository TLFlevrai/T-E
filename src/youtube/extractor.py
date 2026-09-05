# src/youtube/extractor.py
"""Extraction des informations et des flux YouTube.

Récupère les métadonnées d'une vidéo YouTube et sélectionne le flux
approprié (vidéo ≤ 360p ou audio) sans dépendance tierce lourde.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, urlparse

from .exceptions import (
    ExtractionError,
    FormatUnavailableError,
    InvalidYouTubeURLError,
    NetworkError,
    VideoUnavailableError,
)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_MIME_PARTS_MIN_LENGTH = 2

# Patterns pour extraire ytInitialPlayerResponse du HTML YouTube.
_PLAYER_RESPONSE_RE = re.compile(
    r"var\s+ytInitialPlayerResponse\s*=\s*(\{.+?\})\s*;\s*(?:var|</script>)",
    re.DOTALL,
)
_PLAYER_RESPONSE_ALT_RE = re.compile(
    r"ytInitialPlayerResponse\s*=\s*(\{.+?\})\s*;",
    re.DOTALL,
)


# ---------------------------------------------------------------------------
# Modèles de données
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StreamFormat:
    """Un flux vidéo ou audio disponible."""
    itag: int
    url: str
    mime_type: str
    quality_label: str
    width: int
    height: int
    bitrate: int
    audio_quality: str = ""
    content_length: int = 0

    @property
    def is_video(self) -> bool:
        return self.mime_type.startswith("video/")

    @property
    def is_audio(self) -> bool:
        return self.mime_type.startswith("audio/")

    @property
    def container(self) -> str:
        """Extension du conteneur (ex: 'mp4', 'webm', 'm4a')."""
        parts = self.mime_type.split(";")[0].split("/")
        if len(parts) >= _MIME_PARTS_MIN_LENGTH:
            mime = parts[0].lower()
            ext = parts[1].lower()
            if ext == "webm":
                return "webm"
            if ext == "mp4":
                # audio/mp4 → m4a, video/mp4 → mp4
                return "m4a" if mime == "audio" else "mp4"
            if ext in ("mp4a-latm", "mp4a.40.2"):
                return "m4a"
            return ext
        return "mp4"


@dataclass
class VideoInfo:
    """Informations extraites d'une vidéo YouTube."""
    video_id: str
    title: str
    duration: int
    author: str
    video_streams: list[StreamFormat] = field(default_factory=list)
    audio_streams: list[StreamFormat] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Validation d'URL
# ---------------------------------------------------------------------------

_YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}


def validate_url(url: str) -> str:
    """Valide une URL YouTube et retourne l'ID de la vidéo.

    Raises:
        InvalidYouTubeURLError si l'URL n'est pas une URL YouTube valide.
    """
    if not url or not isinstance(url, str):
        raise InvalidYouTubeURLError("L'URL ne peut pas être vide.")

    url = url.strip()
    if not url.startswith(("http://", "https://")):
        raise InvalidYouTubeURLError(
            "L'URL doit commencer par http:// ou https://."
        )

    try:
        parsed = urlparse(url)
    except ValueError as exc:
        raise InvalidYouTubeURLError(f"URL mal formée : {exc}") from exc

    host = (parsed.hostname or "").lower()
    if host not in _YOUTUBE_HOSTS:
        raise InvalidYouTubeURLError(
            f"Ce n'est pas une URL YouTube : {host}"
        )

    video_id = _extract_video_id(parsed)
    if not video_id:
        raise InvalidYouTubeURLError(
            "Impossible d'extraire l'ID de la vidéo depuis cette URL."
        )

    return video_id


def _extract_video_id(parsed: urlparse) -> str | None:
    """Extrait l'ID de la vidéo depuis un URL parsée."""
    host = (parsed.hostname or "").lower()

    # Cas youtu.be/VIDEO_ID
    if host == "youtu.be":
        video_id = parsed.path.lstrip("/").split("/")[0]
        return video_id if video_id else None

    # Cas youtube.com/watch?v=VIDEO_ID
    query = parse_qs(parsed.query)
    if "v" in query:
        return query["v"][0]

    # Cas youtube.com/embed/VIDEO_ID ou youtube.com/v/VIDEO_ID
    path_parts = parsed.path.strip("/").split("/")
    for i, part in enumerate(path_parts):
        if part in ("embed", "v") and i + 1 < len(path_parts):
            return path_parts[i + 1]

    return None


# ---------------------------------------------------------------------------
# Extraction des informations
# ---------------------------------------------------------------------------

def extract_video_info(url: str) -> VideoInfo:
    """Récupère les informations d'une vidéo YouTube.

    Args:
        url: URL YouTube de la vidéo.

    Returns:
        Un objet VideoInfo contenant les métadonnées et les flux disponibles.

    Raises:
        InvalidYouTubeURLError: Si l'URL n'est pas valide.
        VideoUnavailableError: Si la vidéo n'est pas disponible.
        ExtractionError: Si l'extraction échoue.
        NetworkError: Si une erreur réseau survient.
    """
    video_id = validate_url(url)
    page_url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        html = _fetch_page(page_url)
    except urllib.error.HTTPError as exc:
        raise NetworkError(
            f"Erreur HTTP {exc.code} lors de la récupération de la page."
        ) from exc
    except urllib.error.URLError as exc:
        raise NetworkError(
            f"Erreur réseau : {exc.reason}"
        ) from exc

    player_response = _parse_player_response(html)
    if player_response is None:
        raise ExtractionError(
            "Impossible d'extraire les données de la vidéo depuis la page."
        )

    return _build_video_info(video_id, player_response)


def _fetch_page(url: str) -> str:
    """Récupère le contenu HTML d'une page."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _parse_player_response(html: str) -> dict[str, Any] | None:
    """Extrait ytInitialPlayerResponse du HTML YouTube."""
    # Essayer le pattern principal
    match = _PLAYER_RESPONSE_RE.search(html)
    if match is None:
        # Essayer le pattern alternatif (moins strict)
        match = _PLAYER_RESPONSE_ALT_RE.search(html)
    if match is None:
        return None

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None

    return data


def _build_video_info(video_id: str, data: dict[str, Any]) -> VideoInfo:
    """Construit un VideoInfo à partir de la réponse player."""
    video_details = data.get("videoDetails", {})

    title = video_details.get("title", "video")
    duration = int(video_details.get("lengthSeconds", 0))
    author = video_details.get("author", "unknown")

    # Vérifier la disponibilité
    playability = data.get("playabilityStatus", {})
    status = playability.get("status", "")
    if status == "ERROR":
        reason = playability.get("reason", "Vidéo indisponible.")
        raise VideoUnavailableError(reason)
    if status == "UNPLAYABLE":
        reason = playability.get("reason", "La vidéo ne peut pas être lue.")
        raise VideoUnavailableError(reason)

    streaming_data = data.get("streamingData", {})
    formats = streaming_data.get("formats", [])
    adaptive = streaming_data.get("adaptiveFormats", [])

    video_streams: list[StreamFormat] = []
    audio_streams: list[StreamFormat] = []

    # Flux muxés (vidéo + audio ensemble)
    for fmt in formats:
        stream = _parse_stream(fmt)
        if stream is None:
            continue
        if stream.is_video:
            video_streams.append(stream)
        elif stream.is_audio:
            audio_streams.append(stream)

    # Flux adaptatifs (vidéo seule ou audio seul)
    for fmt in adaptive:
        stream = _parse_stream(fmt)
        if stream is None:
            continue
        if stream.is_video:
            video_streams.append(stream)
        elif stream.is_audio:
            audio_streams.append(stream)

    return VideoInfo(
        video_id=video_id,
        title=title,
        duration=duration,
        author=author,
        video_streams=video_streams,
        audio_streams=audio_streams,
    )


def _parse_stream(fmt: dict[str, Any]) -> StreamFormat | None:
    """Parse un format de flux YouTube en StreamFormat."""
    url = fmt.get("url")
    if not url:
        # Les formats signés nécessitent une décodage supplémentaire.
        # On les ignore pour simplifier (cas rare pour les formats de base).
        return None

    mime_type = fmt.get("mimeType", "")
    quality_label = fmt.get("qualityLabel", "")

    width = fmt.get("width", 0) or 0
    height = fmt.get("height", 0) or 0
    bitrate = fmt.get("bitrate", 0) or 0
    audio_quality = fmt.get("audioQuality", "")
    content_length = int(fmt.get("contentLength", 0) or 0)

    itag = fmt.get("itag", 0)

    return StreamFormat(
        itag=itag,
        url=url,
        mime_type=mime_type,
        quality_label=quality_label,
        width=width,
        height=height,
        bitrate=bitrate,
        audio_quality=audio_quality,
        content_length=content_length,
    )


# ---------------------------------------------------------------------------
# Sélection de format
# ---------------------------------------------------------------------------

def select_video_stream(info: VideoInfo, max_height: int = 360) -> StreamFormat:
    """Sélectionne le meilleur flux vidéo ≤ max_height.

    Priorité :
    1. Flux muxés (vidéo + audio) à la meilleure résolution ≤ max_height
    2. Si aucun muxé : flux adaptatif vidéo ≤ max_height

    Raises:
        FormatUnavailableError: Si aucun flux vidéo convenable n'est trouvé.
    """
    # Chercher d'abord les flux muxés (contiennent déjà l'audio)
    muxed = [s for s in info.video_streams if s.height > 0 and s.height <= max_height]
    # Trier par hauteur décroissante, puis par bitrate décroissant
    muxed.sort(key=lambda s: (s.height, s.bitrate), reverse=True)

    if muxed:
        return muxed[0]

    # Aucun flux muxé trouvé
    raise FormatUnavailableError(
        f"Aucun flux vidéo disponible en {max_height}p ou moins. "
        f"Résolutions disponibles : {_available_resolutions(info)}"
    )


def select_audio_stream(info: VideoInfo) -> StreamFormat:
    """Sélectionne le meilleur flux audio disponible.

    Priorité :
    1. Flux audio m4a (meilleur codec pour MP3)
    2. Flux audio webm (opus)
    3. N'importe quel autre flux audio

    Raises:
        FormatUnavailableError: Si aucun flux audio n'est trouvé.
    """
    if not info.audio_streams:
        raise FormatUnavailableError("Aucun flux audio disponible pour cette vidéo.")

    # Trier par bitrate décroissant
    sorted_audio = sorted(info.audio_streams, key=lambda s: s.bitrate, reverse=True)

    # Préférer m4a/mp4 pour une meilleure compatibilité
    m4a_streams = [s for s in sorted_audio if "mp4" in s.mime_type.lower()]
    if m4a_streams:
        return m4a_streams[0]

    return sorted_audio[0]


def _available_resolutions(info: VideoInfo) -> str:
    """Retourne les résolutions disponibles sous forme de chaîne."""
    heights = sorted({s.height for s in info.video_streams if s.height > 0})
    if not heights:
        return "aucune"
    return ", ".join(f"{h}p" for h in heights)

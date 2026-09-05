# tests/unit/test_youtube.py
"""Tests unitaires pour le module YouTube."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.youtube.exceptions import (
    ExtractionError,
    FormatUnavailableError,
    InvalidYouTubeURLError,
    NetworkError,
    VideoUnavailableError,
)
from src.youtube.extractor import (
    StreamFormat,
    VideoInfo,
    _extract_video_id,
    _parse_stream,
    select_audio_stream,
    select_video_stream,
    validate_url,
)


# ---------------------------------------------------------------------------
# Tests de validation d'URL
# ---------------------------------------------------------------------------

class TestValidateURL:
    """Tests pour validate_url()."""

    def test_watch_url_standard(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        video_id = validate_url(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_watch_url_no_www(self):
        url = "https://youtube.com/watch?v=abc123DEF"
        video_id = validate_url(url)
        assert video_id == "abc123DEF"

    def test_watch_url_with_params(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
        video_id = validate_url(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_youtu_be_short_url(self):
        url = "https://youtu.be/dQw4w9WgXcQ"
        video_id = validate_url(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_youtu_be_with_params(self):
        url = "https://youtu.be/dQw4w9WgXcQ?si=abc123"
        video_id = validate_url(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_embed_url(self):
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        video_id = validate_url(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_mobile_url(self):
        url = "https://m.youtube.com/watch?v=dQw4w9WgXcQ"
        video_id = validate_url(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_http_url(self):
        url = "http://www.youtube.com/watch?v=dQw4w9WgXcQ"
        video_id = validate_url(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_empty_url_raises(self):
        with pytest.raises(InvalidYouTubeURLError):
            validate_url("")

    def test_none_url_raises(self):
        with pytest.raises(InvalidYouTubeURLError):
            validate_url(None)  # type: ignore[arg-type]

    def test_no_protocol_raises(self):
        with pytest.raises(InvalidYouTubeURLError):
            validate_url("youtube.com/watch?v=abc")

    def test_non_youtube_url_raises(self):
        with pytest.raises(InvalidYouTubeURLError):
            validate_url("https://www.vimeo.com/123456")

    def test_non_youtube_url_dailymotion(self):
        with pytest.raises(InvalidYouTubeURLError):
            validate_url("https://www.dailymotion.com/video/x12345")

    def test_invalid_query_no_v(self):
        with pytest.raises(InvalidYouTubeURLError):
            validate_url("https://www.youtube.com/watch?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf")

    def test_www_prefix(self):
        url = "https://www.youtube.com/watch?v=abc123"
        video_id = validate_url(url)
        assert video_id == "abc123"


# ---------------------------------------------------------------------------
# Tests de sélection de format
# ---------------------------------------------------------------------------

class TestSelectVideoStream:
    """Tests pour select_video_stream()."""

    def _make_stream(self, height: int, bitrate: int = 500000, **kwargs) -> StreamFormat:
        return StreamFormat(
            itag=kwargs.get("itag", 18),
            url="https://example.com/stream",
            mime_type=kwargs.get("mime_type", "video/mp4"),
            quality_label=f"{height}p",
            width=kwargs.get("width", 640),
            height=height,
            bitrate=bitrate,
            audio_quality=kwargs.get("audio_quality", "audio: 128kbps"),
        )

    def test_select_360p_when_available(self):
        streams = [
            self._make_stream(720),
            self._make_stream(480),
            self._make_stream(360),
            self._make_stream(240),
        ]
        info = VideoInfo(
            video_id="test",
            title="Test",
            duration=100,
            author="test",
            video_streams=streams,
        )
        result = select_video_stream(info, max_height=360)
        assert result.height == 360

    def test_select_best_below_360p(self):
        streams = [
            self._make_stream(720),
            self._make_stream(480),
        ]
        info = VideoInfo(
            video_id="test",
            title="Test",
            duration=100,
            author="test",
            video_streams=streams,
        )
        with pytest.raises(FormatUnavailableError):
            select_video_stream(info, max_height=360)

    def test_select_highest_quality_when_no_max(self):
        streams = [
            self._make_stream(240),
            self._make_stream(360),
            self._make_stream(480),
        ]
        info = VideoInfo(
            video_id="test",
            title="Test",
            duration=100,
            author="test",
            video_streams=streams,
        )
        result = select_video_stream(info, max_height=480)
        assert result.height == 480

    def test_no_streams_raises(self):
        info = VideoInfo(
            video_id="test",
            title="Test",
            duration=100,
            author="test",
            video_streams=[],
        )
        with pytest.raises(FormatUnavailableError):
            select_video_stream(info)

    def test_prefers_muxed_stream(self):
        muxed = self._make_stream(360, audio_quality="audio: 128kbps")
        adaptive = StreamFormat(
            itag=134,
            url="https://example.com/stream",
            mime_type="video/mp4",
            quality_label="360p",
            width=640,
            height=360,
            bitrate=500000,
            audio_quality="",
        )
        info = VideoInfo(
            video_id="test",
            title="Test",
            duration=100,
            author="test",
            video_streams=[muxed, adaptive],
        )
        result = select_video_stream(info, max_height=360)
        assert result.audio_quality != ""


class TestSelectAudioStream:
    """Tests pour select_audio_stream()."""

    def _make_audio_stream(self, bitrate: int, mime: str = "audio/mp4") -> StreamFormat:
        return StreamFormat(
            itag=140,
            url="https://example.com/audio",
            mime_type=mime,
            quality_label="audio",
            width=0,
            height=0,
            bitrate=bitrate,
            audio_quality="AUDIO_QUALITY_MEDIUM",
        )

    def test_select_highest_bitrate(self):
        streams = [
            self._make_audio_stream(64000),
            self._make_audio_stream(128000),
            self._make_audio_stream(256000),
        ]
        info = VideoInfo(
            video_id="test",
            title="Test",
            duration=100,
            author="test",
            audio_streams=streams,
        )
        result = select_audio_stream(info)
        assert result.bitrate == 256000

    def test_no_audio_streams_raises(self):
        info = VideoInfo(
            video_id="test",
            title="Test",
            duration=100,
            author="test",
            audio_streams=[],
        )
        with pytest.raises(FormatUnavailableError):
            select_audio_stream(info)

    def test_prefers_m4a_over_webm(self):
        webm = self._make_audio_stream(128000, "audio/webm")
        m4a = self._make_audio_stream(128000, "audio/mp4")
        info = VideoInfo(
            video_id="test",
            title="Test",
            duration=100,
            author="test",
            audio_streams=[webm, m4a],
        )
        result = select_audio_stream(info)
        assert "mp4" in result.mime_type.lower()


# ---------------------------------------------------------------------------
# Tests de StreamFormat
# ---------------------------------------------------------------------------

class TestStreamFormat:
    """Tests pour StreamFormat."""

    def test_is_video(self):
        fmt = StreamFormat(
            itag=18, url="", mime_type="video/mp4",
            quality_label="360p", width=640, height=360, bitrate=500000,
        )
        assert fmt.is_video is True
        assert fmt.is_audio is False

    def test_is_audio(self):
        fmt = StreamFormat(
            itag=140, url="", mime_type="audio/mp4",
            quality_label="audio", width=0, height=0, bitrate=128000,
            audio_quality="AUDIO_QUALITY_MEDIUM",
        )
        assert fmt.is_audio is True
        assert fmt.is_video is False

    def test_container_mp4(self):
        fmt = StreamFormat(
            itag=18, url="", mime_type="video/mp4",
            quality_label="360p", width=640, height=360, bitrate=500000,
        )
        assert fmt.container == "mp4"

    def test_container_webm(self):
        fmt = StreamFormat(
            itag=251, url="", mime_type="audio/webm",
            quality_label="audio", width=0, height=0, bitrate=128000,
        )
        assert fmt.container == "webm"

    def test_container_m4a(self):
        fmt = StreamFormat(
            itag=140, url="", mime_type="audio/mp4",
            quality_label="audio", width=0, height=0, bitrate=128000,
        )
        assert fmt.container == "m4a"


# ---------------------------------------------------------------------------
# Tests de parsing de flux
# ---------------------------------------------------------------------------

class TestParseStream:
    """Tests pour _parse_stream()."""

    def test_parse_valid_stream(self):
        fmt = {
            "itag": 18,
            "url": "https://example.com/video",
            "mimeType": "video/mp4; codecs=\"avc1.42001E, mp4a.40.2\"",
            "qualityLabel": "360p",
            "width": 640,
            "height": 360,
            "bitrate": 500000,
            "audioQuality": "AUDIO_QUALITY_MEDIUM",
            "contentLength": "12345678",
        }
        result = _parse_stream(fmt)
        assert result is not None
        assert result.itag == 18
        assert result.url == "https://example.com/video"
        assert result.height == 360
        assert result.content_length == 12345678

    def test_parse_stream_without_url(self):
        fmt = {
            "itag": 18,
            "mimeType": "video/mp4",
            "qualityLabel": "360p",
            "width": 640,
            "height": 360,
            "bitrate": 500000,
        }
        result = _parse_stream(fmt)
        assert result is None

    def test_parse_stream_defaults(self):
        fmt = {
            "itag": 18,
            "url": "https://example.com/video",
            "mimeType": "video/mp4",
        }
        result = _parse_stream(fmt)
        assert result is not None
        assert result.quality_label == ""
        assert result.width == 0
        assert result.height == 0
        assert result.bitrate == 0


# ---------------------------------------------------------------------------
# Tests d'extraction (avec mock)
# ---------------------------------------------------------------------------

class TestExtractVideoInfo:
    """Tests pour extract_video_info() avec mock réseau."""

    @patch("src.youtube.extractor._fetch_page")
    def test_extract_basic_info(self, mock_fetch):
        player_response = {
            "videoDetails": {
                "videoId": "abc123",
                "title": "Test Video",
                "lengthSeconds": "120",
                "author": "Test Channel",
            },
            "playabilityStatus": {"status": "OK"},
            "streamingData": {
                "formats": [
                    {
                        "itag": 18,
                        "url": "https://example.com/video",
                        "mimeType": "video/mp4",
                        "qualityLabel": "360p",
                        "width": 640,
                        "height": 360,
                        "bitrate": 500000,
                        "audioQuality": "AUDIO_QUALITY_MEDIUM",
                    }
                ],
                "adaptiveFormats": [],
            },
        }
        html = f"var ytInitialPlayerResponse = {json.dumps(player_response)}; var something"
        mock_fetch.return_value = html

        from src.youtube.extractor import extract_video_info
        info = extract_video_info("https://www.youtube.com/watch?v=abc123")

        assert info.video_id == "abc123"
        assert info.title == "Test Video"
        assert info.duration == 120
        assert info.author == "Test Channel"
        assert len(info.video_streams) == 1
        assert info.video_streams[0].height == 360

    @patch("src.youtube.extractor._fetch_page")
    def test_extract_unavailable_video(self, mock_fetch):
        player_response = {
            "videoDetails": {"videoId": "abc123", "title": "Test"},
            "playabilityStatus": {
                "status": "ERROR",
                "reason": "Vidéo privée.",
            },
            "streamingData": {},
        }
        html = f"var ytInitialPlayerResponse = {json.dumps(player_response)}; var something"
        mock_fetch.return_value = html

        from src.youtube.extractor import extract_video_info
        with pytest.raises(VideoUnavailableError, match="privée"):
            extract_video_info("https://www.youtube.com/watch?v=abc123")

    @patch("src.youtube.extractor._fetch_page")
    def test_extract_no_player_response(self, mock_fetch):
        mock_fetch.return_value = "<html><body>Page sans données</body></html>"

        from src.youtube.extractor import extract_video_info
        with pytest.raises(ExtractionError):
            extract_video_info("https://www.youtube.com/watch?v=abc123")


# ---------------------------------------------------------------------------
# Tests d'intégration réseau (marqués comme network)
# ---------------------------------------------------------------------------

@pytest.mark.network
class TestNetworkIntegration:
    """Tests nécessitant une connexion réseau.

    Ces tests utilisent de vraies URL YouTube et peuvent échouer
    si la connexion est indisponible ou si YouTube change son API.
    """

    def test_validate_real_url(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        video_id = validate_url(url)
        assert video_id == "dQw4w9WgXcQ"

    @pytest.mark.slow
    def test_extract_real_video(self):
        from src.youtube.extractor import extract_video_info
        info = extract_video_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert info.video_id == "dQw4w9WgXcQ"
        assert info.title  # Le titre ne devrait pas être vide
        assert info.duration > 0
        assert len(info.video_streams) > 0 or len(info.audio_streams) > 0

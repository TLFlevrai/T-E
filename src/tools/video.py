# src/tools/video.py
"""Outil Vidéo : convertisseur vidéo → MP3 (dialogue spécialisé conservé)."""
from __future__ import annotations

from src.core.command_registry import Command
from src.core.tool import Tool


def _open_video(shell) -> None:
    from src.gui.video_converter import open_video_converter
    open_video_converter(shell.root)


TOOL = Tool(
    id='video',
    name="Vidéo",
    description="Convertir des vidéos en fichiers MP3.",
    category="Médias",
    icon='🎬',
    shortcut='Ctrl+3',
    open=_open_video,
    keywords=('video', 'mp3', 'audio', 'convertir', 'convert'),
)


def register(reg, cmds) -> None:
    reg.register(TOOL)
    cmds.register(Command(
        id='tool.video',
        label="Vidéo",
        description="Convertir des vidéos en fichiers MP3",
        shortcut='Ctrl+3',
        icon='🎬',
        tool_id='video',
        keywords=('video', 'mp3', 'audio', 'convertir', 'convert'),
    ))

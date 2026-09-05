# src/gui/network_center/models.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from typing import Optional


@dataclass
class FileItem:
    """Fichier envoyable."""
    display_name: str
    full_path: Path
    size: int
    
    @property
    def name(self) -> str:
        return self.full_path.name


@dataclass
class Peer:
    """Pair découvert sur le réseau."""
    ip: str
    hostname: str
    
    @property
    def display_name(self) -> str:
        return f"{self.hostname} ({self.ip})"


@dataclass
class SendHistoryEntry:
    """Entrée d'historique d'envoi."""
    timestamp: str
    filename: str
    peer: str
    status: str  # "Succès" | "Échec" | "En cours"

    def format_line(self) -> str:
        return f"[{self.timestamp}] {self.filename} → {self.peer} : {self.status}"
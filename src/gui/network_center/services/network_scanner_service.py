# src/gui/network_center/services/network_scanner_service.py
from __future__ import annotations
from typing import Dict, List
from ..models import Peer
from src.network.discovery import DiscoveryService
from src.logger import setup_logger

logger = setup_logger(__name__)


class NetworkScannerService:
    """Service de scan réseau (wrapper autour de DiscoveryService)."""
    
    def __init__(self, discovery: DiscoveryService):
        self.discovery = discovery
    
    def scan(self, timeout: int = 2) -> List[Peer]:
        """Effectue un scan et retourne la liste des peers."""
        try:
            raw_peers = self.discovery.scan(timeout=timeout)
            return [Peer(ip=ip, hostname=hostname) for ip, hostname in raw_peers.items()]
        except Exception as e:
            logger.error(f"Erreur scan réseau : {e}")
            return []
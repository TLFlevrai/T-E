# src/gui/network_center/views/__init__.py
from __future__ import annotations
from .file_list_view import FileListView
from .peer_list_view import PeerListView
from .send_controls_view import SendControlsView
from .history_view import HistoryView

__all__ = [
    'FileListView',
    'PeerListView', 
    'SendControlsView',
    'HistoryView'
]
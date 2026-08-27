# src/gui/network_center/send_tab.py
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from typing import Optional
from src.i18n import _
from src.logger import setup_logger
from ..errors import show_info, show_error

from .models import FileItem, Peer, SendHistoryEntry
from .services.file_listing_service import FileListingService
from .services.network_scanner_service import NetworkScannerService
from .services.file_transfer_service import FileTransferService, TransferResult
from .views.file_list_view import FileListView
from .views.peer_list_view import PeerListView
from .views.send_controls_view import SendControlsView
from .views.history_view import HistoryView

logger = setup_logger(__name__)


class SendTab(ttk.Frame):
    """
    Onglet "Envoyer" - Compositeur MVP (Model-View-Presenter).
    Orchestre les vues et services, gère le threading UI.
    """
    
    def __init__(self, parent, dialog, discovery, output_dir, lazy=False):
        super().__init__(parent)
        self.dialog = dialog
        self.output_dir = output_dir

        # Services
        self.file_service = FileListingService(output_dir)
        self.network_service = NetworkScannerService(discovery)
        self.transfer_service = FileTransferService()

        # État
        self.selected_file: Optional[FileItem] = None
        self.selected_peer: Optional[Peer] = None

        self._create_views()
        self._layout_views()

        # Chargement initial : différé à la première affichage de l'onglet
        # quand lazy=True (évite rglob + scan réseau à l'ouverture du dialogue).
        if not lazy:
            self.initial_load()

    def initial_load(self):
        """Chargement initial (appelé une fois, quand l'onglet est affiché)."""
        if getattr(self, '_initial_loaded', False):
            return
        self._initial_loaded = True
        self.refresh_files()
        self.scan_network()
    
    def _create_views(self):
        self.file_view = FileListView(self, self._on_file_selected)
        self.peer_view = PeerListView(self, self._on_peer_selected)
        self.controls = SendControlsView(
            self,
            on_send=self._start_send,
            on_refresh_files=self.refresh_files,
            on_scan_network=self.scan_network
        )
        self.history = HistoryView(self)
    
    def _layout_views(self):
        # Grid layout principal
        self.file_view.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        self.peer_view.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        self.controls.grid(row=2, column=0, columnspan=2, pady=10)
        self.history.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(3, weight=1)
    
    def _marshal(self, fn):
        """Planifie fn sur le thread UI ; vérifie l'existence du dialogue
        DANS le callback (jamais depuis le thread worker)."""
        def run():
            if self.winfo_exists():
                fn()
        try:
            self.dialog.after(0, run)
        except tk.TclError:
            pass
    
    # --- Callbacks Vues ---
    
    def _on_file_selected(self, item: Optional[FileItem]):
        self.selected_file = item
        self._update_send_button()
    
    def _on_peer_selected(self, peer: Optional[Peer]):
        self.selected_peer = peer
        self._update_send_button()
    
    def _update_send_button(self):
        ready = self.selected_file is not None and self.selected_peer is not None
        self.controls.set_send_enabled(ready)
    
    # --- Actions Publiques ---
    
    def refresh_files(self):
        """Recharge la liste des fichiers locaux."""
        self.controls.set_status(_("Actualisation fichiers..."))
        items = self.file_service.list_files()
        self.file_view.populate(items)
        self.selected_file = None
        self._update_send_button()
        self.controls.set_status(_("Prêt"))
        logger.info(f"{len(items)} fichiers disponibles")
    
    def scan_network(self):
        """Lance un scan réseau asynchrone."""
        self.controls.set_status(_("Scan réseau en cours..."))
        # Thread pour ne pas bloquer l'UI
        import threading
        threading.Thread(target=self._scan_worker, daemon=True).start()
    
    def _scan_worker(self):
        peers = self.network_service.scan(timeout=2)
        self._marshal(lambda: self._scan_finished(peers))
    
    def _scan_finished(self, peers):
        self.peer_view.populate(peers)
        self.selected_peer = None
        self._update_send_button()
        count = len(peers)
        self.controls.set_status(f"{count} PC trouvé(s)" if count else _("Aucun PC trouvé"))
    
    def _start_send(self):
        if not (self.selected_file and self.selected_peer):
            return
        
        self.controls.set_send_enabled(False)
        self.controls.set_progress(0)
        self.controls.set_status(_("Envoi en cours..."))
        
        self.transfer_service.send_file(
            file_path=self.selected_file.full_path,
            peer_ip=self.selected_peer.ip,
            progress_callback=self._on_progress,
            result_callback=self._on_transfer_complete
        )
    
    def _on_progress(self, current: int, total: int):
        percent = (current / total * 100) if total > 0 else 0
        self._marshal(lambda: self.controls.set_progress(percent))

    def _on_transfer_complete(self, result: TransferResult):
        def ui_update():
            self.controls.set_send_enabled(True)

            if result.success:
                self.controls.set_status(_("Envoi réussi"))
                self.controls.set_progress(100)
                self.history.add_entry(SendHistoryEntry(
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    filename=self.selected_file.name if self.selected_file else "?",
                    peer=self.selected_peer.display_name if self.selected_peer else "?",
                    status=_("Succès")
                ))
                show_info(
                    _("Succès"),
                    _("Fichier envoyé à {} ({})").format(
                        self.selected_peer.hostname if self.selected_peer else "?",
                        self.selected_peer.ip if self.selected_peer else "?"
                    ),
                    parent=self
                )
                logger.info(f"Fichier envoyé à {self.selected_peer.hostname if self.selected_peer else '?'}")
            else:
                self.controls.set_status(_("Échec de l'envoi"))
                self.controls.set_progress(0)
                self.history.add_entry(SendHistoryEntry(
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    filename=self.selected_file.name if self.selected_file else "?",
                    peer=self.selected_peer.display_name if self.selected_peer else "?",
                    status=_("Échec")
                ))
                show_error(_("Erreur"), result.error_message, parent=self, log=False)
                logger.error(result.error_message)

        self._marshal(ui_update)
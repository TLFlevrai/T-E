# src/core/app.py
"""Composition Root de TE.

Instancie et connecte tous les services techniques (réseau, extraction),
puis démarre le Shell (sidebar + workspace). Point d'entrée central de
l'application, indépendant de l'identité des outils.
"""
from __future__ import annotations

import tkinter as tk
from pathlib import Path

from src.config import config
from src.extractor.extractor import CodeExtractor
from src.i18n import setup_i18n
from src.logger import setup_logger
from src.network.discovery import DiscoveryService
from src.network.server import ReceiveServer
from src.services.extraction_service import ExtractionService
from src.versioning import VersionManager

logger = setup_logger(__name__)


class Application:
    """Service d'application : gère le cycle de vie des services techniques.

    Composition Root : instancie et connecte toutes les dépendances.
    """

    def __init__(self) -> None:
        self.root: tk.Tk | None = None
        self.shell = None
        self.server: ReceiveServer | None = None
        self.discovery: DiscoveryService | None = None

    def start(self) -> None:
        """Démarre l'application complète."""
        # 0. Activation High-DPI AVANT la création de la fenêtre (rendu net 4K)
        from src.gui.premium import setup_dpi_awareness
        setup_dpi_awareness()

        # 1. Initialisation i18n AVANT création GUI
        setup_i18n()

        # 2. Création fenêtre Tkinter
        self.root = tk.Tk()

        # 3. Garde-fous : crash handler global + guard des callbacks Tk
        from src.gui.app_guard import install_excepthook, install_thread_excepthook, install_tk_callback_guard
        from src.gui.crash_report import show_crash_dialog
        install_excepthook(on_crash=lambda details: show_crash_dialog(self.root, details))
        install_thread_excepthook()
        install_tk_callback_guard(self.root, on_crash=lambda details: show_crash_dialog(self.root, details))

        # 4. Démarrage services réseau (AVANT GUI pour éviter race conditions UI)
        self._start_network_services()

        # 5. Composition Root : créer les dépendances du domaine
        extraction_service = self._create_extraction_service()

        # 6. Création du Shell TE (sidebar + workspace + outils)
        from src.ui.shell import TEShell
        self.shell = TEShell(
            root=self.root,
            server=self.server,
            discovery=self.discovery,
            extraction_service=extraction_service,
        )

        # 7. Gestion fermeture propre
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # 8. Boucle principale
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            logger.info("Interruption clavier reçue")
        finally:
            self._stop_network_services()

    def _create_extraction_service(self) -> ExtractionService:
        """Composition Root pour le service d'extraction (Domain/Use-Case layer)."""
        output_dir = Path(config.get('output_dir', 'out'))
        version_file = config.get('version_file', 'extractor_version.txt')

        version_manager = VersionManager(version_file)
        code_extractor = CodeExtractor()

        return ExtractionService(
            extractor=code_extractor,
            version_manager=version_manager,
            output_dir=output_dir,
        )

    def _start_network_services(self) -> None:
        """Démarre les services réseau avec configuration centralisée."""
        try:
            output_dir = Path(config.get('output_dir', 'out'))
            received_subdir = config.get('received_subdir', 'received')
            received_dir = output_dir / received_subdir

            self.server = ReceiveServer(
                host=config.get('network.server_host', '127.0.0.1'),
                port=config.get('network.server_port', 50000),
                received_dir=received_dir,
            )
            self.server.start()
            logger.info("Serveur réseau démarré sur %s:%s", self.server.host, self.server.port)

            self.discovery = DiscoveryService(
                listen_port=config.get('network.discovery_port', 50001),
            )
            self.discovery.start_listener()
            logger.info("Service de découverte réseau démarré")

        except Exception as e:
            logger.error("Erreur lors du démarrage des services réseau : %s", e)
            self._stop_network_services()
            raise

    def _stop_network_services(self) -> None:
        """Arrêt propre et ordonné des services réseau."""
        logger.info("Arrêt des services réseau...")

        if self.discovery:
            try:
                self.discovery.stop_listener()
                logger.info("Service de découverte arrêté")
            except Exception as e:
                logger.error("Erreur arrêt discovery : %s", e)

        if self.server:
            try:
                self.server.stop()
                logger.info("Serveur réseau arrêté")
            except Exception as e:
                logger.error("Erreur arrêt serveur : %s", e)

    def _on_close(self) -> None:
        """Callback fermeture fenêtre - délègue au shell."""
        if self.shell:
            self.shell.on_close()
        self._stop_network_services()
        if self.root:
            self.root.destroy()


def main() -> None:
    """Point d'entrée principal."""
    Application().start()


if __name__ == "__main__":
    main()

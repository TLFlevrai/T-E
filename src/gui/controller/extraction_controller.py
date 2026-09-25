# src/gui/controller/extraction_controller.py
from __future__ import annotations
import threading
from .base_controller import BaseController
from src.gui.extraction_runner import run_extraction
from src.gui.recent_files import add_recent_folder
from ..errors import show_error, show_warning
from src.i18n import _
from src.logger import setup_logger

logger = setup_logger(__name__)

class ExtractionController(BaseController):
    """Orchestration de l'extraction de code."""
    
    def __init__(self, root, ui_widgets, service=None):
        super().__init__(root, ui_widgets, service)
        self._cancel_event = None

    def open_selection_dialog(self):
        """Ouvre le dialogue de sélection des fichiers."""
        if not self._selected_folder:
            show_warning(_("Attention"), _("Veuillez d'abord sélectionner un dossier"), parent=self.root)
            return

        from src.gui.file_selector import select_files
        options = self.get_include_options()
        selected = select_files(self.root, self._selected_folder, options)

        if selected is not None:
            self.selected_files = selected
            count = len(selected)
            self.add_info(_("Sélection mise à jour : {} fichier(s) sélectionné(s)").format(count))
            self.update_status(_("Sélection : {} fichier(s)").format(count))
        else:
            self.add_info(_("Sélection annulée"))

    def extract_code(self, export_pdf=False):
        """Lance l'extraction du code, optionnellement avec export PDF."""
        if not self._selected_folder:
            show_warning(_("Attention"), _("Veuillez d'abord sélectionner un dossier"), parent=self.root)
            return

        if self.is_extracting:
            return

        self.set_extracting(True)
        self._do_extraction(export_pdf)

    def cancel_extraction(self):
        """Demande l'annulation de l'extraction en cours."""
        if self._cancel_event is not None:
            self._cancel_event.set()
            self.add_info(_("Annulation demandée..."))
            self.update_status(_("Annulation en cours..."))
            # Ne pas désactiver le bouton ici : le thread UI fera le ménage

    def _do_extraction(self, export_pdf=False):
        """Exécute l'extraction dans un thread séparé."""
        options = self.get_extraction_options()
        selected = self.selected_files if self.selected_files else None

        # Récupérer le dossier de sortie personnalisé si défini
        custom_output_dir = None
        custom_path = self.ui.custom_output_dir.get().strip()
        if custom_path:
            from pathlib import Path
            custom_output_dir = Path(custom_path)

        self._cancel_event = threading.Event()
        self.update_status(_("Extraction en cours..."))
        self.add_info(_("\n--- Extraction en cours ---") + (" (PDF)" if export_pdf else ""))

        def extraction_thread():
            try:
                success, output_filename, stats = run_extraction(
                    controller=self,
                    service=self.service,
                    selected_folder=self._selected_folder,
                    options=options,
                    selected_files=selected,
                    progress_callback=None,  # Maintenant géré dans run_extraction
                    export_pdf=export_pdf,
                    cancel_event=self._cancel_event,
                    output_dir=custom_output_dir,
                )

                self.root.after(0, lambda s=success, f=output_filename, st=stats:
                                self._extraction_finished(s, f, st))
            except Exception as e:
                logger.error(f"Erreur dans le thread d'extraction : {e}")
                self.root.after(0, lambda err=e: self._extraction_error(err))

        threading.Thread(target=extraction_thread, daemon=True).start()

    def _extraction_finished(self, success, output_filename, stats):
        """Appelé après la fin de l'extraction."""
        self.ui.progress_var.set(0)
        self._cancel_event = None
        self.set_extracting(False)

        if success:
            self.update_status(_("Extraction terminée"))
            add_recent_folder(self._selected_folder)
            if self.ui.update_recent_menu:
                self.ui.update_recent_menu()
        elif success is None:
            # Annulée par l'utilisateur
            self.update_status(_("Extraction annulée"))
            self.add_info(_("Extraction annulée par l'utilisateur"))
        else:
            self.update_status(_("Extraction échouée"))

    def _extraction_error(self, error):
        """Appelé en cas d'erreur dans le thread d'extraction."""
        self.ui.progress_var.set(0)
        self._cancel_event = None
        self.set_extracting(False)
        self.update_status(_("Extraction échouée"))
        show_error(_("Erreur"), _("Une erreur est survenue : {}").format(error), parent=self.root)

    def export_to_pdf(self):
        """Lance l'extraction et génère un PDF."""
        if not self._selected_folder:
            show_warning(_("Attention"), _("Veuillez d'abord sélectionner un dossier"), parent=self.root)
            return

        if self.is_extracting:
            return

        self.set_extracting(True)
        self._do_extraction(export_pdf=True)
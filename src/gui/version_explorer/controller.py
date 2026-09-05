# src/gui/version_explorer/controller.py
"""Contrôleur du gestionnaire de versions : logique métier sans UI."""
from __future__ import annotations
import threading
from typing import Callable, Dict, List, Optional

from src.i18n import _
from src.logger import setup_logger
from src.services.version_service import VersionArchiveService, VersionEntry

logger = setup_logger(__name__)


class VersionExplorerController:
    """
    Logique métier du gestionnaire de versions.
    Communique avec la vue via des callbacks (UI thread uniquement).
    """

    def __init__(
        self,
        service: Optional[VersionArchiveService] = None,
        on_status: Optional[Callable[[str], None]] = None,
        on_projects_loaded: Optional[Callable[[Dict[str, List[VersionEntry]]], None]] = None,
        on_error: Optional[Callable[[str, str], None]] = None,
        on_info: Optional[Callable[[str, str], None]] = None,
    ):
        """
        Args:
            service: Service de gestion des versions
            on_status: Callback (str) pour mettre à jour la barre de statut
            on_projects_loaded: Callback (dict) appelé après scan, avec le projet courant en clé
            on_error: Callback (titre, message) pour afficher une erreur
            on_info: Callback (titre, message) pour afficher une information
        """
        self.service = service or VersionArchiveService()
        self.projects_data: Dict[str, List[VersionEntry]] = {}
        self.current_project: Optional[str] = None

        self.on_status = on_status
        self.on_projects_loaded = on_projects_loaded
        self.on_error = on_error
        self.on_info = on_info

    def _run_in_thread(self, target, *args, **kwargs):
        """Lance une tâche métier dans un thread."""
        threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True).start()

    def _post(self, callback, *args):
        """Appelle un callback si défini."""
        if callback:
            callback(*args)

    # --- Scan ---

    def start_scan(self):
        self._post(self.on_status, _("Scan des fichiers en cours..."))
        self._run_in_thread(self._scan)

    def _scan(self):
        try:
            self.projects_data = self.service.scan_projects()
            self._post(self.on_projects_loaded, self.projects_data)
        except Exception as e:
            logger.error("Erreur lors du scan : %s", e)
            self._post(self.on_error, _("Erreur"), _("Impossible de scanner les fichiers : {}").format(e))

    # --- Actions ---

    def archive_selected(self, entries):
        self._post(self.on_status, _("Archivage en cours..."))
        self._run_in_thread(self._archive, entries)

    def _archive(self, entries):
        try:
            for entry in entries:
                self.service.archive(entry)
            self._post(self.on_status, _("Mise a jour terminee"))
            self._post(self.on_projects_loaded, self.service.scan_projects())
        except Exception as e:
            logger.error("Erreur lors de l'archivage : %s", e)
            self._post(self.on_error, _("Erreur d'archivage"), str(e))

    def restore_selected(self, entries):
        self._post(self.on_status, _("Restauration en cours..."))
        self._run_in_thread(self._restore, entries)

    def _restore(self, entries):
        try:
            for entry in entries:
                self.service.restore(entry)
            self._post(self.on_status, _("Mise a jour terminee"))
            self._post(self.on_projects_loaded, self.service.scan_projects())
        except Exception as e:
            logger.error("Erreur lors de la restauration : %s", e)
            self._post(self.on_error, _("Erreur de restauration"), str(e))

    def delete_selected(self, entries):
        self._post(self.on_status, _("Suppression en cours..."))
        self._run_in_thread(self._delete, entries)

    def _delete(self, entries):
        try:
            for entry in entries:
                self.service.delete(entry)
            self._post(self.on_status, _("Mise a jour terminee"))
            self._post(self.on_projects_loaded, self.service.scan_projects())
        except Exception as e:
            logger.error("Erreur lors de la suppression : %s", e)
            self._post(self.on_error, _("Erreur de suppression"), str(e))

    def clean_all(self):
        self._post(self.on_status, _("Nettoyage complet en cours..."))
        self._run_in_thread(self._clean_all)

    def _clean_all(self):
        try:
            count = self.service.clean_all()
            self._post(self.on_status, _("Nettoyage termine : {} fichier(s) supprime(s)").format(count))
            self._post(self.on_projects_loaded, self.service.scan_projects())
            self._post(self.on_info, _("Nettoyage termine"),
                       _("Tous les exports ont ete supprimes.\n{} fichier(s) supprime(s).").format(count))
        except Exception as e:
            logger.error("Erreur lors du nettoyage complet : %s", e)
            self._post(self.on_error, _("Erreur de nettoyage"), str(e))

    def reset_counter(self, project_name: str):
        try:
            self.service.reset_project(project_name)
            self._post(self.on_status, _("Compteur reinitialise pour {}").format(project_name))
            self._post(self.on_projects_loaded, self.service.scan_projects())
        except Exception as e:
            logger.error("Erreur lors de la reinitialisation : %s", e)
            self._post(self.on_error, _("Erreur"), str(e))

    # --- Refresh ---

    def refresh(self):
        self._post(self.on_status, _("Rafraichissement..."))
        self._run_in_thread(self._refresh)

    def _refresh(self):
        try:
            self.projects_data = self.service.scan_projects()
            self._post(self.on_projects_loaded, self.projects_data)
            self._post(self.on_status, _("Mise a jour terminee"))
        except Exception as e:
            logger.error("Erreur lors du rafraichissement : %s", e)
            self._post(self.on_error, _("Erreur de rafraichissement"), str(e))

    def refresh_after_action(self):
        """Re-scan synchrone utilisé après les actions qui modifient les fichiers."""
        try:
            self.projects_data = self.service.scan_projects()
            self._post(self.on_projects_loaded, self.projects_data)
            self._post(self.on_status, _("Mise a jour terminee"))
            return True
        except Exception as e:
            logger.error("Erreur lors du re-scan : %s", e)
            self._post(self.on_error, _("Erreur"), str(e))
            return False

    def get_output_dir(self):
        return self.service.output_dir
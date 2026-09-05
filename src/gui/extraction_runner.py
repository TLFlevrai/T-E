# src/gui/extraction_runner.py
from __future__ import annotations
import os
import time
from pathlib import Path
from typing import Callable, Optional, Tuple
import tkinter as tk
from src.i18n import _
from src.logger import setup_logger
from src.services.pdf_service import PDFService
from .errors import show_error, show_info
from .toast import show_toast

logger = setup_logger(__name__)

ProgressCallback = Callable[[int, int, str], None]
LogCallback = Callable[[str], None]

# Seuil pour afficher une ETA (sinon on reste sur le simple pourcentage)
ETA_THRESHOLD_SECONDS = 1.5

# Intervalle minimal entre deux rafraîchissements UI planifiés depuis le
# thread de travail. Sans cela, un projet de plusieurs milliers de fichiers
# empile des milliers de callbacks after() et l'UI continue de "tourner"
# après la fin de l'extraction.
UI_UPDATE_INTERVAL_SECONDS = 0.06


def _format_eta(seconds: float) -> str:
    """Formate une durée en secondes vers 'Xmin Ys' ou 'Ys'."""
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}min {secs}s"
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins}min"


def run_extraction(controller, service, selected_folder, options, selected_files,
                    progress_callback: ProgressCallback, log_callback: LogCallback,
                    export_pdf: bool = False,
                    cancel_event=None) -> Tuple[Optional[bool], Optional[str], Optional[dict]]:
    """
    Exécute l'extraction via le service dans le THREAD APPELANT (worker).
    Toutes les mutations de l'interface sont marshallées sur le thread UI
    via root.after : aucun widget/tk Variable n'est touché depuis ce thread.
    Retourne (success, output_filename, stats) :
      - (True, file, stats) : succès
      - (False, None, None) : échec
      - (None, None, None) : annulé
    Si export_pdf est True, génère également un PDF.
    """
    root = controller.root

    def post(fn: Callable[[], None]) -> None:
        """Planifie fn sur le thread UI (sûr si la fenêtre est déjà détruite)."""
        try:
            root.after(0, fn)
        except tk.TclError:
            pass

    # Estimation du temps restant + throttling des mises à jour UI
    eta_state = {'start_time': None, 'last_current': 0, 'eta': None}
    ui_state = {'last_scheduled': 0.0}

    def enhanced_progress_callback(current: int, total: int, current_file: str = "") -> None:
        """Callback de progression enrichi : pourcentage + ETA."""
        # Démarre le chrono au premier fichier
        if eta_state['start_time'] is None:
            eta_state['start_time'] = time.monotonic()
        else:
            elapsed = time.monotonic() - eta_state['start_time']
            delta = current - eta_state['last_current']
            if current > 0 and delta > 0 and elapsed > ETA_THRESHOLD_SECONDS:
                rate = delta / elapsed
                remaining = (total - current) / rate
                eta_state['eta'] = remaining
        eta_state['last_current'] = current

        # Throttle : au plus ~16 mises à jour/s ; l'état final est garanti par
        # _extraction_finished (côté UI).
        now = time.monotonic()
        finished = total > 0 and current >= total
        if not finished and (now - ui_state['last_scheduled']) < UI_UPDATE_INTERVAL_SECONDS:
            return
        ui_state['last_scheduled'] = now

        def _apply():
            if total > 0:
                controller.ui.progress_var.set((current / total) * 100)
            if current_file:
                if eta_state['eta'] is not None:
                    status_msg = _("Traitement : {} ({}/{}) - ETA {}").format(
                        current_file, current, total, _format_eta(eta_state['eta']))
                else:
                    status_msg = _("Traitement : {} ({}/{})").format(current_file, current, total)
                controller.update_status(_("Extraction en cours..."), status_msg)
            else:
                controller.update_status(_("Extraction en cours..."))

        post(_apply)

    def enhanced_log_callback(msg: str) -> None:
        post(lambda: controller.add_info(msg))

    try:
        success, output_filename, stats = service.extract_folder(
            selected_folder,
            options,
            progress_callback=enhanced_progress_callback,
            log_callback=enhanced_log_callback,
            selected_files=selected_files,
            cancel_event=cancel_event,
        )

        if success is None:
            # Annulée par l'utilisateur
            post(lambda: controller.ui.status_var.set(_("Extraction annulée")))
            post(lambda: controller.ui.progress_var.set(0))
            return None, None, None

        if not success:
            post(lambda: controller.ui.status_var.set(_("Extraction échouée")))
            post(lambda: controller.ui.progress_var.set(0))
            post(lambda: show_error(
                _("Erreur"), _("Échec de l'extraction (voir journal)"), parent=controller.root))
            return False, None, None

        # Succès
        post(lambda: controller.ui.status_var.set(_("Extraction terminée")))
        post(lambda: controller.ui.progress_var.set(0))

        def _log_success_summary():
            controller.add_info(_("\n--- Extraction terminée avec succès ---"))
            controller.add_info(_("Fichier créé : {}").format(output_filename))
            controller.add_info(_("Emplacement : {}").format(os.path.abspath(output_filename)))
            controller.add_info(_("Fichiers extraits : {} (Python: {}, JSON: {}, TXT: {}, PO: {}, MO: {}, HTML: {}, CSS: {}, JS: {})").format(
                stats['total_files'], stats['py_count'], stats['json_count'], stats['txt_count'],
                stats['po_count'], stats['mo_count'], stats['html_count'], stats['css_count'], stats['js_count']
            ))
        post(_log_success_summary)

        # --- Génération du PDF si demandé ---
        pdf_path = None
        if export_pdf:
            txt_path = Path(output_filename)
            pdf_path = txt_path.with_suffix('.pdf')
            post(lambda: controller.add_info(_("Génération du PDF en cours...")))
            try:
                PDFService.convert_to_pdf(txt_path, pdf_path)
                post(lambda: controller.add_info(_("PDF généré : {}").format(pdf_path)))
                post(lambda: controller.add_info(_("Emplacement : {}").format(os.path.abspath(pdf_path))))
            except Exception as e:
                logger.error("Erreur lors de la génération du PDF : %s", e)
                post(lambda e=e: controller.add_info(_("Erreur de génération du PDF : {}").format(e)))

        # Message de succès (inclut le PDF si généré)
        success_msg = (
            _("Extraction terminée avec succès !\n\n")
            + _("Fichier créé : {}\n").format(output_filename)
            + _("Nombre de fichiers extraits : {}\n").format(stats['total_files'])
            + _("  - Fichiers Python : {}\n").format(stats['py_count'])
            + _("  - Fichiers JSON : {}\n").format(stats['json_count'])
            + _("  - Fichiers TXT : {}\n").format(stats['txt_count'])
            + _("  - Fichiers PO : {}\n").format(stats['po_count'])
            + _("  - Fichiers MO : {}\n").format(stats['mo_count'])
            + _("  - Fichiers HTML : {}\n").format(stats['html_count'])
            + _("  - Fichiers CSS : {}\n").format(stats['css_count'])
            + _("  - Fichiers JS : {}\n").format(stats['js_count'])
            + _("Emplacement : {}").format(os.path.abspath(output_filename))
        )
        if export_pdf and pdf_path:
            success_msg += _("\n\nPDF généré : {}").format(os.path.abspath(pdf_path))

        # Toast non-bloquant (déjà sur le thread UI via post) + message de succès
        def _show_success():
            try:
                show_toast(controller.root, _("Extraction terminée avec succès"), 'success')
            except Exception:
                logger.debug("Erreur lors de l'affichage du toast de succès", exc_info=True)
            show_info(_("Succès"), success_msg, parent=controller.root)
        post(_show_success)
        return True, output_filename, stats

    except Exception as e:
        logger.error("Erreur lors de l'extraction : %s", e)
        post(lambda: controller.ui.status_var.set(_("Extraction échouée")))
        post(lambda: controller.ui.progress_var.set(0))
        post(lambda e=e: show_error(
            _("Erreur"), _("Une erreur est survenue : {}").format(e), parent=controller.root))
        return False, None, None

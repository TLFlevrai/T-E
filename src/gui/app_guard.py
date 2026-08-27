# src/gui/app_guard.py
"""
Garde-fous globaux de l'application : crash handler, exceptions des
callbacks Tk, et exécution thread-safe sur l'UI.
"""
import queue
import sys
import threading
import traceback
import tkinter as tk
from typing import Any, Callable, Optional

from src.logger import setup_logger

logger = setup_logger(__name__)


# ---------------------------------------------------------------------------
# Crash handler global
# ---------------------------------------------------------------------------

def install_excepthook(on_crash: Optional[Callable[[str], None]] = None):
    """
    Installe un hook global pour intercepter les exceptions non gérées.
    Log la trace complète et notifie l'utilisateur (callback optionnel).
    """
    def _hook(exc_type, exc_value, exc_tb):
        details = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logger.error("Exception non gérée :\n%s", details)
        if on_crash:
            try:
                on_crash(details)
            except Exception:
                pass

    sys.excepthook = _hook


def install_thread_excepthook():
    """Logue les exceptions non gérées des threads (sinon invisibles : les
    threads daemon font échouer silencieusement les callbacks planifiés)."""

    def _hook(args: threading.ExceptHookArgs):
        if args.exc_type is SystemExit:
            return
        logger.error(
            "Exception non gérée dans le thread %s :\n%s",
            args.thread.name if args.thread is not None else '?',
            "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_tb)),
        )

    threading.excepthook = _hook


def install_tk_callback_guard(root: tk.Tk, on_crash: Optional[Callable[[str], None]] = None):
    """
    Intercepte les exceptions survenues dans les callbacks Tkinter
    (bind, after, command). Sans cela, une exception dans un callback
    est seulement imprimée sur stderr et l'état peut se corrompre.
    """
    def _report(exc_type, exc_value, exc_tb):
        details = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logger.error("Exception dans un callback Tkinter :\n%s", details)
        if on_crash:
            try:
                root.after(0, lambda: on_crash(details))
            except Exception:
                pass

    root.report_callback_exception = _report


# ---------------------------------------------------------------------------
# Exécution thread-safe sur l'UI
# ---------------------------------------------------------------------------

class UIThreadDispatcher:
    """
    Exécute des callbacks sur le thread principal de Tkinter depuis des
    threads de travail, sans collision d'appels `after` et avec purge
    des callbacks obsolètes.
    """

    def __init__(self, root: tk.Misc, max_queue: int = 200):
        self.root = root
        self._queue: queue.Queue = queue.Queue(maxsize=max_queue)
        self._scheduled = False

    def post(self, callback: Callable[[], None], *args: Any):
        """Planifie un callback sur le thread UI (non bloquant)."""
        try:
            self._queue.put_nowait((callback, args))
        except queue.Full:
            # File saturée : on log et on lâche le plus ancien pour éviter un blocage
            logger.warning("File UI saturée, callback abandonné : %s", getattr(callback, '__name__', callback))
            return
        if not self._scheduled:
            self._scheduled = True
            self._schedule()

    def _schedule(self):
        try:
            self.root.after(10, self._drain)
        except Exception:
            self._scheduled = False

    def _drain(self):
        self._scheduled = False
        processed = 0
        while processed < 50:
            try:
                callback, args = self._queue.get_nowait()
            except queue.Empty:
                break
            try:
                callback(*args)
            except Exception as e:
                logger.error("Erreur dans un callback UI dispatché : %s\n%s",
                             e, traceback.format_exc())
            processed += 1
        if not self._queue.empty():
            self._scheduled = True
            self._schedule()

    @staticmethod
    def is_main_thread() -> bool:
        return threading.current_thread() is threading.main_thread()


def safe_after(root: tk.Misc, delay_ms: int, callback: Callable[[], None]):
    """
    Equivalent thread-safe de root.after : si appelé depuis un thread de
    travail, requeue le callback sur le thread principal.
    """
    if UIThreadDispatcher.is_main_thread():
        try:
            return root.after(delay_ms, callback)
        except Exception as e:
            logger.error("Erreur dans after() : %s", e)
            return None
    else:
        # Depuis un thread : planifier sur le thread principal
        dispatcher = getattr(root, '_ui_dispatcher', None)
        if dispatcher is None:
            dispatcher = UIThreadDispatcher(root)
            root._ui_dispatcher = dispatcher  # type: ignore[attr-defined]
        dispatcher.post(lambda: root.after(delay_ms, callback))
        return None
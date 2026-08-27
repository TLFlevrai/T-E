# src/core/events.py
"""Bus d'événements simple et typé pour TE.

Permet de découpler les modules : un émetteur publie un événement, les
abonnés reçoivent la notification sans se connaître mutuellement.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class EventBus:
    """Bus d'événements synchrones (même thread) avec abonnement/désabonnement."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[..., None]]] = {}

    def subscribe(self, event: str, callback: Callable[..., None]) -> None:
        """Abonne un callback à un événement."""
        if callback not in self._subscribers.setdefault(event, []):
            self._subscribers[event].append(callback)

    def unsubscribe(self, event: str, callback: Callable[..., None]) -> None:
        """Désabonne un callback d'un événement."""
        callbacks = self._subscribers.get(event)
        if callbacks and callback in callbacks:
            callbacks.remove(callback)

    def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Publie un événement vers tous les abonnés."""
        for callback in list(self._subscribers.get(event, [])):
            try:
                callback(*args, **kwargs)
            except Exception:
                logger.exception("Erreur dans un abonné à l'événement '%s'", event)

    def clear(self) -> None:
        """Supprime tous les abonnements (utile en test)."""
        self._subscribers.clear()


# Instance globale partagée par toute l'application
events = EventBus()

# src/gui/_eta.py
"""Logique pure d'estimation du temps restant (ETA) pour extraction_runner.

Module volontairement sans dépendance Tkinter : testable headless.
"""
from __future__ import annotations

from collections.abc import Iterable

# ETA max : 1 heure (3600 secondes)
MAX_ETA_SECONDS = 3600
_SECONDS_PER_MINUTE = 60
_MINUTES_PER_HOUR = 60


def compute_eta(
    rates: Iterable[float],
    current: int,
    total: int,
    delta: int,
    elapsed: float,
) -> float | None:
    """Met à jour la fenêtre glissante et estime le temps restant (s).

    La vitesse est dérivée de la DERNIÈRE mesure seulement (``delta``
    fichiers en ``elapsed`` secondes), puis lissée par la moyenne
    glissante ``rates``. Un cumul depuis le début du traitement fausse
    l'estimation : les premières mesures lentes (scan du dossier, lecture)
    dominaient la moyenne et l'ETA ne redescendait jamais.

    Args:
        rates: fenêtre glissante (deque borné) des taux instantanés,
            mutée par cette fonction.
        current: fichiers traités à cette mesure.
        total: nombre total de fichiers attendus.
        delta: fichiers traités depuis la mesure précédente.
        elapsed: secondes écoulées depuis la mesure précédente.

    Returns:
        ETA en secondes (bornée à [0, MAX_ETA_SECONDS]), ou None si une
        donnée d'entrée ne permet pas le calcul.
    """
    if total <= 0 or current <= 0 or delta <= 0 or elapsed <= 0:
        return None
    rates.append(delta / elapsed)
    avg_rate = sum(rates) / len(rates)
    if avg_rate <= 0:
        return None
    remaining = (total - current) / avg_rate
    return max(0.0, min(remaining, MAX_ETA_SECONDS))


def format_eta(seconds: float) -> str:
    """Formate une durée en secondes vers 'Xmin Ys' ou 'Ys'."""
    seconds = max(0, int(seconds))
    if seconds < _SECONDS_PER_MINUTE:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, _SECONDS_PER_MINUTE)
    if minutes < _MINUTES_PER_HOUR:
        return f"{minutes}min {secs}s"
    hours, mins = divmod(minutes, _MINUTES_PER_HOUR)
    return f"{hours}h {mins}min"

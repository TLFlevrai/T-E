# tests/unit/test_eta.py
"""Tests unitaires de la logique ETA (lot 1.5) — purs, sans Tkinter."""
from __future__ import annotations

from collections import deque

import pytest

from src.gui._eta import MAX_ETA_SECONDS, compute_eta, format_eta

# Fenêtre glissante du runner (deque maxlen=10) : reproduite ici.
RATE_WINDOW = 10


class TestComputeEta:
    def test_returns_none_on_first_measurement(self):
        # delta=0 : pas de vitesse mesurable au premier appel
        rates = deque(maxlen=RATE_WINDOW)
        assert compute_eta(rates, current=5, total=100,
                           delta=0, elapsed=0.0) is None

    def test_eta_from_instant_rate(self):
        rates = deque(maxlen=RATE_WINDOW)
        # 10 fichiers/s mesurés, 90 restants -> 9s
        eta = compute_eta(rates, current=10, total=100,
                          delta=10, elapsed=1.0)
        assert eta == pytest.approx(9.0)

    def test_sliding_window_smooths_rates(self):
        small_window = 2
        rates = deque(maxlen=small_window)
        first = compute_eta(rates, current=10, total=110,
                            delta=10, elapsed=1.0)   # 10 f/s
        assert first == pytest.approx(10.0)
        second = compute_eta(rates, current=20, total=110,
                             delta=10, elapsed=2.0)   # 5 f/s
        # avg = (10 + 5) / 2 = 7.5 f/s, restants 90 -> 12s
        assert second == pytest.approx(12.0)
        third = compute_eta(rates, current=20, total=110,
                            delta=10, elapsed=2.0)   # rates=[5, 5]
        assert third == pytest.approx(18.0)
        # La fenêtre glissante oublie les vieilles mesures
        assert len(rates) == small_window

    def test_eta_reacts_to_speedup(self):
        """Le vrai bug 1.5 : après une phase lente, un regain de vitesse
        doit faire baisser l'ETA (mesure par appel, pas cumul)."""
        rates = deque(maxlen=RATE_WINDOW)
        # Phase lente : 1 f/s pendant toute la fenêtre
        for i in range(RATE_WINDOW):
            compute_eta(rates, current=i + 1, total=100,
                        delta=1, elapsed=1.0)
        slow_eta = compute_eta(rates, current=RATE_WINDOW, total=100,
                               delta=1, elapsed=1.0)
        # Phase rapide : 50 f/s
        fast_eta = compute_eta(rates, current=60, total=100,
                               delta=50, elapsed=1.0)
        assert slow_eta is not None and fast_eta is not None
        assert fast_eta < slow_eta

    def test_clamped_to_max(self):
        rates = deque(maxlen=RATE_WINDOW)
        # 1 f/s avec 5000 restants -> 5000s, borné à 3600
        eta = compute_eta(rates, current=10, total=5010,
                          delta=1, elapsed=1.0)
        assert eta == MAX_ETA_SECONDS

    def test_clamped_to_zero(self):
        rates = deque(maxlen=RATE_WINDOW)
        # current > total : reste négatif -> 0
        eta = compute_eta(rates, current=120, total=100,
                          delta=10, elapsed=1.0)
        assert eta == 0.0

    @pytest.mark.parametrize("kwargs", [
        {"current": 0, "total": 100, "delta": 5, "elapsed": 1.0},   # current nul
        {"current": 10, "total": 0, "delta": 5, "elapsed": 1.0},    # total nul
        {"current": 10, "total": 100, "delta": 0, "elapsed": 1.0},  # pas d'avancée
        {"current": 10, "total": 100, "delta": 5, "elapsed": 0.0},  # pas de temps
        {"current": 10, "total": 100, "delta": -3, "elapsed": 1.0},  # régression
    ])
    def test_returns_none_on_invalid_inputs(self, kwargs):
        rates = deque(maxlen=RATE_WINDOW)
        assert compute_eta(rates, **kwargs) is None

    def test_rates_window_maxlen_respected(self):
        tiny_window = 3
        rates = deque(maxlen=tiny_window)
        for i in range(1, 6):
            compute_eta(rates, current=i * 10, total=1000,
                        delta=10, elapsed=1.0)
        assert len(rates) == tiny_window


class TestFormatEta:
    def test_seconds(self):
        assert format_eta(45) == "45s"

    def test_zero(self):
        assert format_eta(0) == "0s"

    def test_negative_clamped(self):
        assert format_eta(-5) == "0s"

    def test_minutes(self):
        assert format_eta(90) == "1min 30s"

    def test_hours(self):
        assert format_eta(7200) == "2h 0min"

    def test_hours_and_minutes(self):
        assert format_eta(5400) == "1h 30min"

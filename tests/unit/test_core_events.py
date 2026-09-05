# tests/unit/test_core_events.py
"""Tests unitaires pour le bus d'événements."""
from __future__ import annotations

from src.core.events import EventBus


class TestEventBus:
    """Tests pour EventBus."""

    def test_subscribe_and_emit(self):
        bus = EventBus()
        received = []
        bus.subscribe('test', lambda: received.append('called'))
        bus.emit('test')
        assert received == ['called']

    def test_emit_with_args(self):
        bus = EventBus()
        received = []
        bus.subscribe('test', lambda a, b: received.append((a, b)))
        bus.emit('test', 1, 2)
        assert received == [(1, 2)]

    def test_emit_with_kwargs(self):
        bus = EventBus()
        received = []
        bus.subscribe('test', lambda x=0: received.append(x))
        bus.emit('test', x=42)
        assert received == [42]

    def test_multiple_subscribers(self):
        bus = EventBus()
        results = []
        bus.subscribe('test', lambda: results.append('a'))
        bus.subscribe('test', lambda: results.append('b'))
        bus.emit('test')
        assert results == ['a', 'b']

    def test_unsubscribe(self):
        bus = EventBus()
        received = []
        callback = lambda: received.append('called')
        bus.subscribe('test', callback)
        bus.unsubscribe('test', callback)
        bus.emit('test')
        assert received == []

    def test_unsubscribe_nonexistent(self):
        bus = EventBus()
        callback = lambda: None
        # Ne devrait pas lever d'erreur
        bus.unsubscribe('test', callback)

    def test_emit_unknown_event(self):
        bus = EventBus()
        # Ne devrait pas lever d'erreur
        bus.emit('unknown')

    def test_clear(self):
        bus = EventBus()
        received = []
        bus.subscribe('test', lambda: received.append('called'))
        bus.clear()
        bus.emit('test')
        assert received == []

    def test_no_duplicate_subscribers(self):
        bus = EventBus()
        count = [0]
        callback = lambda: count.__setitem__(0, count[0] + 1)
        bus.subscribe('test', callback)
        bus.subscribe('test', callback)
        bus.emit('test')
        assert count[0] == 1

    def test_exception_in_subscriber_does_not_break_others(self):
        bus = EventBus()
        results = []

        def bad_callback():
            raise ValueError("boom")

        bus.subscribe('test', bad_callback)
        bus.subscribe('test', lambda: results.append('ok'))
        bus.emit('test')
        assert results == ['ok']

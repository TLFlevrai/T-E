# tests/unit/test_core_commands.py
"""Tests unitaires pour le registre de commandes."""
from __future__ import annotations

from src.core.command_registry import Command, CommandRegistry


class TestCommand:
    """Tests pour Command."""

    def test_navigates_with_tool_id(self):
        cmd = Command(id='test', label='Test', tool_id='extract')
        assert cmd.navigates is True

    def test_navigates_without_tool_id(self):
        cmd = Command(id='test', label='Test', handler=lambda s: None)
        assert cmd.navigates is False

    def test_frozen(self):
        cmd = Command(id='test', label='Test')
        try:
            cmd.id = 'other'
            assert False, "Should be frozen"
        except Exception:
            pass


class TestCommandRegistry:
    """Tests pour CommandRegistry."""

    def test_register_and_get(self):
        reg = CommandRegistry()
        cmd = Command(id='test', label='Test')
        reg.register(cmd)
        assert reg.get('test') is cmd

    def test_get_unknown(self):
        reg = CommandRegistry()
        assert reg.get('unknown') is None

    def test_all(self):
        reg = CommandRegistry()
        reg.register(Command(id='a', label='A'))
        reg.register(Command(id='b', label='B'))
        assert len(reg.all()) == 2

    def test_search_by_label(self):
        reg = CommandRegistry()
        reg.register(Command(id='quit', label='Quitter'))
        reg.register(Command(id='copy', label='Copier'))
        results = reg.search('quitter')
        assert len(results) == 1
        assert results[0].id == 'quit'

    def test_search_empty_query(self):
        reg = CommandRegistry()
        reg.register(Command(id='a', label='A'))
        reg.register(Command(id='b', label='B'))
        assert len(reg.search('')) == 2

    def test_search_no_match(self):
        reg = CommandRegistry()
        reg.register(Command(id='quit', label='Quitter'))
        assert reg.search('xyz') == []

    def test_clear(self):
        reg = CommandRegistry()
        reg.register(Command(id='test', label='Test'))
        reg.clear()
        assert reg.all() == []

    def test_execute_navigate(self):
        reg = CommandRegistry()
        cmd = Command(id='test', label='Test', tool_id='extract')
        reg.register(cmd)

        class FakeShell:
            def __init__(self):
                self.shown = None
            def show_tool(self, tid):
                self.shown = tid

        shell = FakeShell()
        reg.execute('test', shell)
        assert shell.shown == 'extract'

    def test_execute_handler(self):
        reg = CommandRegistry()
        results = []
        cmd = Command(id='test', label='Test', handler=lambda s: results.append('done'))
        reg.register(cmd)
        reg.execute('test', None)
        assert results == ['done']

    def test_execute_unknown(self):
        reg = CommandRegistry()
        # Ne devrait pas lever d'erreur
        reg.execute('unknown', None)

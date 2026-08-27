# src/tools/tools_hub.py
"""Outil Outils : hub d'utilitaires et de personnalisation de TE."""
from __future__ import annotations

import os
import shutil
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

from src.config import get_config
from src.core.command_registry import Command
from src.core.tool import Tool
from src.i18n import _
from src.ui.tooltips import ToolTipContent, add_lazy_rich_tooltip


def build_tools_view(shell) -> ttk.Frame:
    """Construit le hub d'utilitaires dans le workspace."""
    frame = ttk.Frame(shell.workspace, padding=16)
    frame.columnconfigure(0, weight=1)

    title = ttk.Label(frame, text=str(_("Outils")),
                      font=('Segoe UI', 15, 'bold'))
    title.grid(row=0, column=0, sticky=tk.W, pady=(0, 14))

    # --- Personnalisation ---
    _section(frame, 1, _("Personnalisation"))

    _card(frame, 2, "🎨", _("Éditeur de thème"),
          _("Personnaliser les couleurs du thème de TE."),
          lambda: _open_theme_editor(shell))
    _card(frame, 3, "🗑️", _("Vider les emplacements récents"),
          _("Efface la liste des dossiers récents."),
          lambda: _clear_recent(shell))
    _card(frame, 4, "Factory", _("Réinitialiser tout (par défaut)"),
          _("Remet la config par défaut et vide le dossier out/."),
          lambda: _reset_to_defaults(shell))

    # --- Extraction ---
    _section(frame, 6, _("Extraction"))

    _card(frame, 7, "📄", _("Exporter en PDF"),
          _("Extrait le projet sélectionné et génère un PDF."),
          lambda: _export_pdf(shell))
    _card(frame, 8, "🧹", _("Effacer le journal"),
          _("Vide le journal d'extraction."),
          lambda: _clear_log(shell))

    presets_frame = ttk.Frame(frame, style='Card.TFrame', padding=(14, 10))
    presets_frame.grid(row=9, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
    presets_frame.columnconfigure(0, weight=1)
    ttk.Label(presets_frame, text=str(_("Preset d'export")),
              style='Card.TLabel', font=('Segoe UI', 10, 'bold')).grid(
        row=0, column=0, columnspan=4, sticky=tk.W, pady=(0, 8))
    presets = [
        ('python_only', "🐍", _("Preset : Python uniquement")),
        ('web_assets', "🌐", _("Preset : Assets Web")),
        ('full', "📦", _("Preset : Complet")),
        ('minimal', "⚡", _("Preset : Minimal")),
    ]
    for i, (preset, icon, label) in enumerate(presets):
        btn = ttk.Button(presets_frame, text=f"{icon}  {label}",
                         style='AppGhost.TButton',
                         command=lambda p=preset: _apply_preset(shell, p))
        btn.grid(row=1, column=i, padx=6, pady=4, sticky=tk.W)
        tip = add_lazy_rich_tooltip(btn, ToolTipContent(
            title=label,
            description=_("Applique ce preset aux options d'extraction."),
            example=_("Les options de l'outil Extraction sont mises à jour immédiatement."),
        ))
        shell._hub_tips = getattr(shell, '_hub_tips', []) + [tip]

    # --- Divers ---
    _section(frame, 11, _("Divers"))
    _card(frame, 12, "📂", _("Ouvrir le dossier de sortie"),
          _("Ouvre le dossier des exports (out/)."),
          lambda: _open_output_dir(shell))

    frame.rowconfigure(13, weight=1)
    return frame


def _section(frame, row: int, label: str):
    ttk.Label(frame, text=label, font=('Segoe UI', 9, 'bold'),
              foreground='#888888').grid(row=row, column=0, sticky=tk.W, pady=(10, 4))


def _card(frame, row: int, icon: str, title: str, description: str, command):
    card = ttk.Frame(frame, style='Card.TFrame', padding=(14, 10))
    card.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 8))
    card.columnconfigure(1, weight=1)

    ttk.Label(card, text=icon, style='Card.TLabel',
              font=('Segoe UI', 14)).grid(row=0, column=0, padx=(0, 10))
    ttk.Label(card, text=title, style='Card.TLabel',
              font=('Segoe UI', 10, 'bold')).grid(row=0, column=1, sticky=tk.W)
    ttk.Label(card, text=description, style='Card.TLabel',
              font=('Segoe UI', 9)).grid(row=1, column=1, sticky=tk.W)
    button = ttk.Button(card, text=str(_("Ouvrir")), style='AppGhost.TButton',
                        command=command)
    button.grid(row=0, column=2, rowspan=2, padx=(10, 0))


# --- Handlers ---

def _open_theme_editor(shell) -> None:
    from src.gui.theme_editor import open_theme_editor
    open_theme_editor(shell.root)


def _export_pdf(shell) -> None:
    controller = getattr(shell, 'extract_controller', None)
    if controller is not None:
        controller.export_to_pdf()


def _clear_log(shell) -> None:
    controller = getattr(shell, 'extract_controller', None)
    if controller is not None:
        controller.clear_info()


def _clear_recent(shell) -> None:
    from src.gui.recent_files import clear_recent_folders
    clear_recent_folders()
    ui = getattr(shell, 'extract_ui', None)
    if ui is not None and getattr(ui, 'update_recent_menu', None):
        ui.update_recent_menu()


def _open_output_dir(shell) -> None:
    from src.gui.errors import show_error
    output_dir = get_config().get('output_dir', 'out')
    if os.path.isdir(output_dir):
        os.startfile(output_dir)
    else:
        show_error(_("Erreur"), _("Le dossier de sortie n'existe pas."), parent=shell.root)


def _apply_preset(shell, preset: str) -> None:
    from src.gui.ui_builder.menus import apply_preset
    ui = getattr(shell, 'extract_ui', None)
    if ui is not None:
        apply_preset(ui, preset)


def _reset_to_defaults(shell) -> None:
    """Remet toute la config par défaut et vide le dossier out/."""
    confirm = messagebox.askyesno(
        _("Réinitialisation complète"),
        _("Cette action va :\n"
          "• Remettre toutes les options par défaut\n"
          "• Vider le dossier out/ (tous les exports supprimés)\n"
          "• Réinitialiser le thème et la langue\n\n"
          "Continuer ?"),
        icon='warning',
        parent=shell.root,
    )
    if not confirm:
        return

    # 1. Vider le dossier out/
    output_dir = get_config().get('output_dir', 'out')
    out_path = Path(output_dir)
    if out_path.exists():
        for child in out_path.iterdir():
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                child.unlink(missing_ok=True)

    # 2. Réinitialiser config.json avec les valeurs par défaut
    from src.config.schema import AppConfig
    default_cfg = AppConfig()
    try:
        import json
        config_path = Path(__file__).parent.parent.parent / "config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_cfg.model_dump(), f, indent=2, ensure_ascii=False)
    except Exception as e:
        messagebox.showerror(_("Erreur"), str(e), parent=shell.root)
        return

    # 3. Reset le singleton config pour forcer le rechargement
    from src.config import _Config
    _Config._reset_for_testing()
    get_config()

    # 4. Vider les emplacements récents
    try:
        from src.gui.recent_files import clear_recent_folders
        clear_recent_folders()
    except Exception:
        pass

    messagebox.showinfo(
        _("Réinitialisation"),
        _("Configuration réinitialisée et dossier out/ vidé.\n"
          "Redémarrez TE pour appliquer le thème par défaut."),
        parent=shell.root,
    )


def _cmd_clear_recent(shell) -> None:
    _clear_recent(shell)


def _cmd_open_output_dir(shell) -> None:
    _open_output_dir(shell)


def _cmd_reset_to_defaults(shell) -> None:
    _reset_to_defaults(shell)


TOOL = Tool(
    id='tools',
    name="Outils",
    description="Utilitaires et personnalisation de TE.",
    category="Personnalisation",
    icon='🧰',
    shortcut='Ctrl+7',
    view=build_tools_view,
    keywords=('utilitaires', 'tools', 'theme', 'preset', 'personnaliser'),
)


def register(reg, cmds) -> None:
    reg.register(TOOL)
    cmds.register(Command(
        id='tool.tools',
        label="Outils",
        description="Utilitaires et personnalisation de TE",
        shortcut='Ctrl+7',
        icon='🧰',
        tool_id='tools',
        keywords=('utilitaires', 'tools', 'theme'),
    ))
    cmds.register(Command(
        id='tools.clear_recent',
        label="Vider les emplacements récents",
        description="Effacer la liste des dossiers récents",
        icon='🗑️',
        keywords=('recents', 'recent', 'vider', 'clear', 'liste'),
        handler=_cmd_clear_recent,
    ))
    cmds.register(Command(
        id='tools.open_output_dir',
        label="Ouvrir le dossier de sortie",
        description="Ouvrir le dossier des exports (out/)",
        icon='📂',
        keywords=('sortie', 'output', 'dossier', 'ouvrir', 'out'),
        handler=_cmd_open_output_dir,
    ))
    cmds.register(Command(
        id='tools.reset_defaults',
        label="Réinitialiser tout",
        description="Remettre la config par défaut et vider out/",
        icon='Factory',
        keywords=('reset', 'default', 'réinitialiser', 'par défaut', 'factory'),
        handler=_cmd_reset_to_defaults,
    ))

# src/gui/ui_builder/widgets.py
import tkinter as tk
from tkinter import ttk
from src.i18n import _, LazyString, register_reload_callback, unregister_reload_callback
from .ui_widgets import UIWidgets
from .tooltip import add_lazy_tooltip
from .log_widget import LogWidget


def build_widgets(parent, ui: UIWidgets):
    main_frame = ttk.Frame(parent, padding=16)
    main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    ui.main_frame = main_frame

    # --- En-tête compact ---
    title_label = ttk.Label(main_frame, text=str(LazyString("Extracteur de code")),
                            font=('Segoe UI', 15, 'bold'))
    title_label.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 14))
    register_lazy_widget(ui, title_label, "Extracteur de code")

    # --- Carte dossier ---
    folder_card = ttk.Frame(main_frame, style='Card.TFrame', padding=(10, 8))
    folder_card.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 12))
    folder_card.columnconfigure(1, weight=1)

    folder_label = ttk.Label(folder_card, text=str(LazyString("Dossier")), style='Card.TLabel')
    folder_label.grid(row=0, column=0, padx=(0, 10))
    register_lazy_widget(ui, folder_label, "Dossier")

    folder_entry = ttk.Entry(folder_card, textvariable=ui.folder_path_var,
                             state='readonly', font=('Segoe UI', 10))
    folder_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
    ui.folder_entry = folder_entry

    browse_btn = ttk.Button(folder_card, text=str(LazyString("Parcourir")),
                            style='AppGhost.TButton')
    browse_btn.grid(row=0, column=2, padx=(10, 0))
    ui.browse_btn = browse_btn
    register_lazy_widget(ui, browse_btn, "Parcourir")
    tooltip = add_lazy_tooltip(browse_btn, "Sélectionner le dossier à scanner (Ctrl+O)")
    ui._lazy_tooltips.append(tooltip)

    # --- Actions : bouton principal + secondaires discrets ---
    action_frame = ttk.Frame(main_frame)
    action_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 12))

    extract_btn = ttk.Button(action_frame, text=str(LazyString("Extraire le code")),
                             style='AppPrimary.TButton', state='disabled')
    extract_btn.pack(side=tk.LEFT, padx=(0, 6))
    ui.extract_btn = extract_btn
    register_lazy_widget(ui, extract_btn, "Extraire le code")
    tooltip = add_lazy_tooltip(extract_btn, "Lancer l'extraction du code (Ctrl+E)")
    ui._lazy_tooltips.append(tooltip)

    cancel_btn = ttk.Button(action_frame, text=str(LazyString("Annuler")),
                            style='AppGhost.TButton', state='disabled')
    cancel_btn.pack(side=tk.LEFT, padx=6)
    ui.cancel_btn = cancel_btn
    register_lazy_widget(ui, cancel_btn, "Annuler")
    tooltip = add_lazy_tooltip(cancel_btn, "Annuler l'extraction en cours")
    ui._lazy_tooltips.append(tooltip)

    select_btn = ttk.Button(action_frame, text=str(LazyString("Sélectionner...")),
                            style='AppGhost.TButton')
    select_btn.pack(side=tk.LEFT, padx=6)
    ui.select_btn = select_btn
    register_lazy_widget(ui, select_btn, "Sélectionner...")
    tooltip = add_lazy_tooltip(select_btn, "Choisir les fichiers spécifiques à extraire")
    ui._lazy_tooltips.append(tooltip)

    version_btn = ttk.Button(action_frame, text=str(LazyString("Versions")),
                             style='AppGhost.TButton')
    version_btn.pack(side=tk.LEFT, padx=6)
    ui.version_btn = version_btn
    register_lazy_widget(ui, version_btn, "Versions")
    tooltip = add_lazy_tooltip(version_btn, "Ouvrir le gestionnaire de versions d'export")
    ui._lazy_tooltips.append(tooltip)

    network_btn = ttk.Button(action_frame, text=str(LazyString("Réseau")),
                             style='AppGhost.TButton')
    network_btn.pack(side=tk.LEFT, padx=6)
    ui.network_btn = network_btn
    register_lazy_widget(ui, network_btn, "Réseau")
    tooltip = add_lazy_tooltip(network_btn, "Ouvrir le centre de transfert réseau")
    ui._lazy_tooltips.append(tooltip)

    # --- Progression : barre + pourcentage ---
    progress_frame = ttk.Frame(main_frame)
    progress_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 12))
    progress_frame.columnconfigure(0, weight=1)

    progress_bar = ttk.Progressbar(progress_frame, variable=ui.progress_var,
                                   maximum=100)
    progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E))
    ui.progress_bar = progress_bar

    ui.progress_pct_var = tk.StringVar(value="0%")
    pct_label = ttk.Label(progress_frame, textvariable=ui.progress_pct_var,
                          width=5, anchor=tk.E)
    pct_label.grid(row=0, column=1, padx=(10, 0))
    ui.progress_pct_label = pct_label

    def _on_progress(*_):
        ui.progress_pct_var.set(f"{int(round(ui.progress_var.get()))}%")
    ui.progress_var.trace_add('write', _on_progress)

    # --- Journal + barre de statut ---
    log_widget = LogWidget(
        parent=main_frame,
        ui=ui,
        status_var=ui.status_var,
        log_visible_var=ui.log_visible,
    )
    ui.log_widget = log_widget

    main_frame.columnconfigure(0, weight=1)
    main_frame.rowconfigure(4, weight=1)
    parent.columnconfigure(0, weight=1)
    parent.rowconfigure(0, weight=1)

    # Enregistrer le callback de rafraîchissement global
    _register_refresh_callback(ui)


def register_lazy_widget(ui: UIWidgets, widget, msgid: str):
    """Enregistre un widget avec son message pour mise à jour ultérieure."""
    ui._lazy_widgets.append((widget, msgid, 'text'))


def register_lazy_labelframe(ui: UIWidgets, labelframe, msgid: str):
    """Enregistre un LabelFrame avec son message pour mise à jour ultérieure."""
    ui._lazy_widgets.append((labelframe, msgid, 'label'))


def _register_refresh_callback(ui: UIWidgets):
    """Enregistre un callback pour rafraîchir tous les widgets à la volée."""
    def refresh_all_widgets():
        for widget, msgid, attr in ui._lazy_widgets:
            try:
                translated = _(msgid)
                if attr == 'text':
                    widget.config(text=translated)
                elif attr == 'label':
                    widget.config(text=translated)
            except Exception:
                pass  # Widget peut être détruit
        for tooltip in ui._lazy_tooltips:
            try:
                tooltip.refresh()
            except Exception:
                pass

    register_reload_callback(refresh_all_widgets)
    ui._i18n_refresh_callback = refresh_all_widgets


def unregister_refresh_callback(ui: UIWidgets):
    """Désenregistre le callback de rafraîchissement (à appeler à la fermeture)."""
    callback = ui._i18n_refresh_callback
    if callback:
        unregister_reload_callback(callback)
        ui._i18n_refresh_callback = None
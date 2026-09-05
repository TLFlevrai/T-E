# src/tools/color_picker.py
"""Outil Color Picker : sélecteur de couleurs avec conversion HEX/RGB/HSL."""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from src.core.command_registry import Command
from src.core.tool import Tool
from src.i18n import _


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convertit RGB en HEX."""
    return f"#{r:02x}{g:02x}{b:02x}"


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convertit HEX en RGB."""
    h = hex_color.lstrip('#')
    if len(h) == 3:
        h = h[0]*2 + h[1]*2 + h[2]*2
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hsl(r: int, g: int, b: int) -> tuple[int, int, int]:
    """Convertit RGB en HSL (0-360, 0-100, 0-100)."""
    r_n, g_n, b_n = r / 255.0, g / 255.0, b / 255.0
    mx = max(r_n, g_n, b_n)
    mn = min(r_n, g_n, b_n)
    lightness = (mx + mn) / 2.0

    if mx == mn:
        h = s = 0.0
    else:
        d = mx - mn
        s = d / (2.0 - mx - mn) if lightness > 0.5 else d / (mx + mn)
        if mx == r_n:
            h = (g_n - b_n) / d + (6 if g_n < b_n else 0)
        elif mx == g_n:
            h = (b_n - r_n) / d + 2
        else:
            h = (r_n - g_n) / d + 4
        h /= 6.0

    return int(h * 360), int(s * 100), int(lightness * 100)


def _hsl_to_rgb(h: int, s: int, lightness: int) -> tuple[int, int, int]:
    """Convertit HSL en RGB."""
    h_n, s_n, l_n = h / 360.0, s / 100.0, lightness / 100.0

    if s_n == 0:
        r = g = b = l_n
    else:
        def _hue2rgb(p: float, q: float, t: float) -> float:
            if t < 0:
                t += 1.0
            if t > 1:
                t -= 1.0
            if t < 1/6:
                return p + (q - p) * 6.0 * t
            if t < 1/2:
                return q
            if t < 2/3:
                return p + (q - p) * (2.0/3.0 - t) * 6.0
            return p

        q = l_n * (1.0 + s_n) if l_n < 0.5 else l_n + s_n - l_n * s_n
        p = 2.0 * l_n - q
        r = _hue2rgb(p, q, h_n + 1.0/3.0)
        g = _hue2rgb(p, q, h_n)
        b = _hue2rgb(p, q, h_n - 1.0/3.0)

    return int(r * 255), int(g * 255), int(b * 255)


def _is_valid_hex(color: str) -> bool:
    """Vérifie si une chaîne est une couleur HEX valide."""
    color = color.strip()
    if not color.startswith('#'):
        return False
    h = color[1:]
    if len(h) not in (3, 6):
        return False
    return all(c in '0123456789abcdefABCDEF' for c in h)


def build_color_picker_view(shell) -> ttk.Frame:
    """Construit la vue sélecteur de couleurs dans le workspace."""
    frame = ttk.Frame(shell.workspace, padding=12)
    frame.columnconfigure(0, weight=1)

    # --- Prévisualisation ---
    preview_frame = ttk.Frame(frame)
    preview_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
    preview_frame.columnconfigure(0, weight=1)

    color_preview = tk.Canvas(preview_frame, height=80, bg='#3498db',
                               highlightthickness=1, highlightbackground='#888')
    color_preview.grid(row=0, column=0, sticky=(tk.W, tk.E))

    # --- Sélection par image ---
    img_frame = ttk.LabelFrame(frame, text=str(_("Sélection depuis une image")), padding=8)
    img_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
    img_frame.columnconfigure(1, weight=1)

    ttk.Label(img_frame, text=str(_("Image :"))).grid(row=0, column=0, padx=(0, 6))
    img_var = tk.StringVar()
    ttk.Entry(img_frame, textvariable=img_var, state='readonly').grid(
        row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 6))
    ttk.Button(img_frame, text="...", width=3,
               command=lambda: _browse_image(img_var)).grid(row=0, column=2)

    pick_btn = ttk.Button(img_frame, text=str(_("Pipette")), state='disabled')
    pick_btn.grid(row=1, column=0, columnspan=3, pady=(6, 0), sticky=(tk.W, tk.E))

    # --- Saisie manuelle ---
    manual_frame = ttk.LabelFrame(frame, text=str(_("Saisie manuelle")), padding=8)
    manual_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
    manual_frame.columnconfigure(1, weight=1)

    ttk.Label(manual_frame, text="HEX :").grid(row=0, column=0, padx=(0, 6))
    hex_var = tk.StringVar(value='#3498db')
    hex_entry = ttk.Entry(manual_frame, textvariable=hex_var, width=12)
    hex_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 12))

    ttk.Label(manual_frame, text="R :").grid(row=0, column=2, padx=(0, 4))
    r_var = tk.StringVar(value='52')
    r_spin = ttk.Spinbox(manual_frame, from_=0, to=255, textvariable=r_var, width=5)
    r_spin.grid(row=0, column=3, padx=(0, 6))

    ttk.Label(manual_frame, text="G :").grid(row=0, column=4, padx=(0, 4))
    g_var = tk.StringVar(value='152')
    g_spin = ttk.Spinbox(manual_frame, from_=0, to=255, textvariable=g_var, width=5)
    g_spin.grid(row=0, column=5, padx=(0, 6))

    ttk.Label(manual_frame, text="B :").grid(row=0, column=6, padx=(0, 4))
    b_var = tk.StringVar(value='219')
    b_spin = ttk.Spinbox(manual_frame, from_=0, to=255, textvariable=b_var, width=5)
    b_spin.grid(row=0, column=7)

    # HSL
    ttk.Label(manual_frame, text="H :").grid(row=1, column=0, padx=(0, 4), pady=(6, 0))
    h_var = tk.StringVar(value='204')
    h_spin = ttk.Spinbox(manual_frame, from_=0, to=360, textvariable=h_var, width=5)
    h_spin.grid(row=1, column=1, sticky=tk.W, padx=(0, 12), pady=(6, 0))

    ttk.Label(manual_frame, text="S :").grid(row=1, column=2, padx=(0, 4), pady=(6, 0))
    s_var = tk.StringVar(value='76')
    s_spin = ttk.Spinbox(manual_frame, from_=0, to=100, textvariable=s_var, width=5)
    s_spin.grid(row=1, column=3, padx=(0, 6), pady=(6, 0))

    ttk.Label(manual_frame, text="L :").grid(row=1, column=4, padx=(0, 4), pady=(6, 0))
    l_var = tk.StringVar(value='53')
    l_spin = ttk.Spinbox(manual_frame, from_=0, to=100, textvariable=l_var, width=5)
    l_spin.grid(row=1, column=5, pady=(6, 0))

    apply_btn = ttk.Button(manual_frame, text=str(_("Appliquer")))
    apply_btn.grid(row=1, column=6, columnspan=2, padx=(12, 0), pady=(6, 0))

    # --- Informations ---
    info_frame = ttk.LabelFrame(frame, text=str(_("Informations")), padding=8)
    info_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
    info_frame.columnconfigure(1, weight=1)

    info_labels = {}
    labels = [
        ("HEX", "hex_info"),
        ("RGB", "rgb_info"),
        ("HSL", "hsl_info"),
        ("CSS", "css_info"),
    ]
    for i, (label_text, key) in enumerate(labels):
        ttk.Label(info_frame, text=f"{label_text} :").grid(
            row=i, column=0, sticky=tk.W, padx=(0, 6))
        var = tk.StringVar()
        ttk.Label(info_frame, textvariable=var, font=('Consolas', 10)).grid(
            row=i, column=1, sticky=tk.W)
        info_labels[key] = var

    # --- Palette récente ---
    recent_frame = ttk.LabelFrame(frame, text=str(_("Couleurs récentes")), padding=8)
    recent_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

    recent_canvas = tk.Canvas(recent_frame, height=30, bg='#2D2D30',
                               highlightthickness=0)
    recent_canvas.pack(fill=tk.X)

    # --- État interne ---
    state = {
        'current_color': '#3498db',
        'recent_colors': [],
        'image_path': None,
        'picking': False,
    }

    def _update_preview(hex_color: str) -> None:
        """Met à jour la prévisualisation et les informations."""
        state['current_color'] = hex_color
        color_preview.configure(bg=hex_color)

        try:
            r, g, b = _hex_to_rgb(hex_color)
            h, s, lightness = _rgb_to_hsl(r, g, b)
        except (ValueError, IndexError):
            return

        r_var.set(str(r))
        g_var.set(str(g))
        b_var.set(str(b))
        h_var.set(str(h))
        s_var.set(str(s))
        l_var.set(str(lightness))

        info_labels['hex_info'].set(hex_color.upper())
        info_labels['rgb_info'].set(f"rgb({r}, {g}, {b})")
        info_labels['hsl_info'].set(f"hsl({h}, {s}%, {lightness}%)")
        info_labels['css_info'].set(f"color: {hex_color};")

    def _on_apply():
        """Applique la couleur saisie manuellement."""
        hex_color = hex_var.get().strip()
        if not _is_valid_hex(hex_color):
            messagebox.showwarning(
                str(_("Couleur invalide")),
                str(_("Entrez une couleur HEX valide (ex: #3498db).")))
            return
        _update_preview(hex_color)
        _add_recent(hex_color)

    def _on_rgb_change(*_args):
        """Met à jour depuis les valeurs RGB."""
        try:
            r = int(r_var.get())
            g = int(g_var.get())
            b = int(b_var.get())
            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))
            hex_color = _rgb_to_hex(r, g, b)
            hex_var.set(hex_color)
            _update_preview(hex_color)
        except (ValueError, TypeError):
            pass

    def _on_hex_change(*_args):
        """Met à jour depuis la valeur HEX."""
        hex_color = hex_var.get().strip()
        if _is_valid_hex(hex_color):
            _update_preview(hex_color)

    def _add_recent(hex_color: str) -> None:
        """Ajoute une couleur à la palette récente."""
        if hex_color in state['recent_colors']:
            state['recent_colors'].remove(hex_color)
        state['recent_colors'].insert(0, hex_color)
        state['recent_colors'] = state['recent_colors'][:12]
        _draw_recent()

    def _draw_recent() -> None:
        """Dessine la palette des couleurs récentes."""
        recent_canvas.delete('all')
        w = recent_canvas.winfo_width()
        if w < 10:
            return
        n = len(state['recent_colors'])
        if n == 0:
            return
        cell_w = max(1, min(40, w // n))
        for i, color in enumerate(state['recent_colors']):
            x0 = i * cell_w
            x1 = x0 + cell_w - 2
            recent_canvas.create_rectangle(x0, 0, x1, 28, fill=color, outline='#555')
            recent_canvas.tag_bind(
                f'rect_{i}', '<Button-1>',
                lambda _e, c=color: _update_preview(c))

    def _browse_image(var):
        path = filedialog.askopenfilename(
            title=str(_("Sélectionner une image")),
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"),
                ("Tous les fichiers", "*.*")])
        if path:
            var.set(path)
            state['image_path'] = path
            pick_btn.config(state='normal')

    def _start_picking():
        """Active le mode pipette."""
        if state['picking']:
            return
        state['picking'] = True
        pick_btn.config(state='normal', text=str(_("Cliquer sur l'image...")))

        try:
            from PIL import Image, ImageTk
            img = Image.open(state['image_path'])
            # Redimensionner pour l'affichage
            max_size = (400, 300)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

            picker_win = tk.Toplevel(frame)
            picker_win.title(str(_("Pipette de couleur")))
            picker_win.attributes('-topmost', True)

            canvas = tk.Canvas(picker_win, width=img.width, height=img.height)
            canvas.pack()

            tk_img = ImageTk.PhotoImage(img)
            canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)
            canvas.image = tk_img  # Garder une référence

            def _on_click(event):
                # Obtenir la couleur du pixel cliqué
                x, y = event.x, event.y
                if 0 <= x < img.width and 0 <= y < img.height:
                    pixel = img.getpixel((x, y))
                    if len(pixel) >= 3:
                        hex_color = _rgb_to_hex(pixel[0], pixel[1], pixel[2])
                        hex_var.set(hex_color)
                        _update_preview(hex_color)
                        _add_recent(hex_color)
                picker_win.destroy()
                state['picking'] = False
                pick_btn.config(state='normal', text=str(_("Pipette")))

            canvas.bind('<Button-1>', _on_click)

            def _on_close():
                state['picking'] = False
                pick_btn.config(state='normal', text=str(_("Pipette")))
                picker_win.destroy()

            picker_win.protocol("WM_DELETE_WINDOW", _on_close)

        except ImportError:
            messagebox.showinfo(
                str(_("PIL requis")),
                str(_("L'image PIL est requise pour la pipette.\n"
                      "Installez-la avec : pip install Pillow")))
            state['picking'] = False
            pick_btn.config(state='normal', text=str(_("Pipette")))

    # Connecter les événements
    r_var.trace_add('write', _on_rgb_change)
    g_var.trace_add('write', _on_rgb_change)
    b_var.trace_add('write', _on_rgb_change)
    hex_var.trace_add('write', _on_hex_change)
    apply_btn.config(command=_on_apply)
    pick_btn.config(command=_start_picking)

    # Initialiser l'affichage
    _update_preview(state['current_color'])

    return frame


TOOL = Tool(
    id='color_picker',
    name="Prisme",
    description="Sélecteur de couleurs avec conversion HEX/RGB/HSL.",
    category="Édition",
    icon='🌈',
    shortcut='Ctrl+Shift+C',
    view=build_color_picker_view,
    keywords=('color', 'couleur', 'hex', 'rgb', 'hsl', 'pipette', 'picker', 'prisme'),
    order=2,
)


def register(reg, cmds) -> None:
    reg.register(TOOL)
    cmds.register(Command(
        id='tool.color_picker',
        label="Prisme",
        description="Sélecteur de couleurs avec conversion HEX/RGB/HSL",
        shortcut='Ctrl+Shift+C',
        icon='🌈',
        tool_id='color_picker',
        keywords=('color', 'couleur', 'hex', 'rgb', 'hsl', 'prisme'),
    ))

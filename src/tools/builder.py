# src/tools/builder.py
"""Outil Builder : reconstituer un projet à partir d'un journal T-E.

Parse un fichier d'extraction généré par Text Exporter et recrée
la structure du projet dans un répertoire de destination.
Version robuste avec validation, dry-run, sélection partielle et annulation.
"""
from __future__ import annotations

import base64
import json
import re
import tkinter as tk
from pathlib import Path
from threading import Thread
from tkinter import filedialog, messagebox, ttk
from typing import Any

from src.core.command_registry import Command
from src.core.tool import Tool
from src.gui.app_guard import safe_after
from src.i18n import _
from src.logger import setup_logger

logger = setup_logger(__name__)

# ── Constantes ──────────────────────────────────────────────────────────────

# Extensions binaires à ignorer (ne peuvent pas être reconstruites)
BINARY_EXTENSIONS = frozenset({
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.webp', '.svg',
    '.mp3', '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm',
    '.wav', '.ogg', '.flac', '.aac',
    '.zip', '.tar', '.gz', '.bz2', '.7z', '.rar',
    '.exe', '.dll', '.so', '.dylib',
    '.pyc', '.pyo', '.class', '.o', '.obj',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.ttf', '.otf', '.woff', '.woff2',
})

# Dossiers à ignorer
IGNORED_DIRS = frozenset({
    '.git', '__pycache__', '.pytest_cache', '.mypy_cache',
    '.ruff_cache', 'node_modules', '.venv', 'venv', '.env',
    'out', 'dist', 'build', '.tox', '.eggs',
    '.coverage', 'htmlcov', '.svn', '.idea', '.vscode',
})

# Patterns de détection de sections (plusieurs variantes supportées)
_SECTION_SPLITTER = re.compile(r"\n={10,}\nFICHIER\s+")
_HEADER_LINE_RE = re.compile(r"^(\w+)\s*:\s*(.+)$")
_SOURCE_FOLDER_RE = re.compile(r"Extraction du code du dossier\s*:\s*(.+?)\n")
_DATE_RE = re.compile(r"Date d'extraction\s*:\s*(.+?)\n")
_FORMAT_VERSION_RE = re.compile(r"Format-Version\s*:\s*(\d+)")

# Patterns de contenu
_MO_BASE64_RE = re.compile(
    r"//\s*Fichier binaire\s*\(\.mo\)\s*encodé en base64\n(.+?)(?=\n---\s*FIN DU FICHIER)",
    re.DOTALL,
)
_SEPARATOR_RE = re.compile(r"\n-{40,}\n")
_END_MARKER = "--- FIN DU FICHIER ---"

_MANIFEST_NAME = ".builder_manifest.json"


# ── Classes de données ──────────────────────────────────────────────────────

class ParsedFile:
    """Représente un fichier extrait du journal."""

    __slots__ = ('rel_path', 'full_path', 'file_type', 'content',
                 'parent_dir', 'size_hint', 'line_count')

    def __init__(
        self,
        rel_path: str,
        full_path: str,
        file_type: str,
        content: str,
        parent_dir: str = '',
        size_hint: str = '',
        line_count: int = 0,
    ):
        self.rel_path = rel_path
        self.full_path = full_path
        self.file_type = file_type
        self.content = content
        self.parent_dir = parent_dir
        self.size_hint = size_hint
        self.line_count = line_count

    @property
    def extension(self) -> str:
        return Path(self.rel_path).suffix.lower()

    @property
    def is_binary(self) -> bool:
        return self.extension in BINARY_EXTENSIONS

    @property
    def is_ignored_dir(self) -> bool:
        """Vérifie si le chemin contient un dossier à ignorer."""
        parts = Path(self.rel_path).parts
        return any(part in IGNORED_DIRS for part in parts)

    @property
    def should_ignore(self) -> bool:
        """Vérifie si ce fichier doit être ignoré."""
        return self.is_ignored_dir or self.is_binary

    @property
    def size_bytes(self) -> int:
        """Taille estimée en octets depuis le contenu."""
        return len(self.content.encode('utf-8', errors='replace'))

    def to_dict(self) -> dict[str, Any]:
        """Serialise en dict pour le manifest."""
        return {
            'rel_path': self.rel_path,
            'full_path': self.full_path,
            'file_type': self.file_type,
            'parent_dir': self.parent_dir,
            'size_hint': self.size_hint,
            'line_count': self.line_count,
        }


class BuildPlan:
    """Plan de construction avec statistiques."""

    def __init__(self) -> None:
        self.files: list[ParsedFile] = []
        self.original_folder: str | None = None
        self.extraction_date: str | None = None
        self.format_version: int = 0  # 0 = legacy (v0), 1 = v1
        self.total_files = 0
        self.binary_count = 0
        self.ignored_count = 0
        self.text_count = 0
        self.conflicts: list[tuple[str, str]] = []  # (path, reason)

    def add_file(self, f: ParsedFile) -> None:
        self.files.append(f)
        self.total_files += 1
        if f.is_binary:
            self.binary_count += 1
        elif f.is_ignored_dir:
            self.ignored_count += 1
        else:
            self.text_count += 1

    def summary(self) -> dict[str, Any]:
        return {
            'total': self.total_files,
            'text': self.text_count,
            'binary': self.binary_count,
            'ignored': self.ignored_count,
            'conflicts': len(self.conflicts),
            'original_folder': self.original_folder,
            'extraction_date': self.extraction_date,
            'format_version': self.format_version,
        }


# ── Parsing robuste ─────────────────────────────────────────────────────────

def validate_log(content: str) -> tuple[bool, str]:
    """Valide qu'un contenu semble être un journal T-E.

    Returns:
        (est_valide, message_erreur)
    """
    if not content or not content.strip():
        return False, str(_("Le fichier est vide."))

    if not _SOURCE_FOLDER_RE.search(content):
        return False, str(_("En-tête T-E introuvable (pas de 'Extraction du code du dossier')."))

    if _END_MARKER not in content:
        return False, str(_("Marqueur de fin de fichier introuvable."))

    # Vérifier Format-Version si présent
    version_match = _FORMAT_VERSION_RE.search(content)
    if version_match:
        version = int(version_match.group(1))
        if version != 1:
            return False, str(_("Format-Version {version} non supportée. Seule la version 1 est gérée.").format(version=version))

    # Vérifier qu'il y a au moins une section
    sections = _SECTION_SPLITTER.split(content)
    if len(sections) < 2:
        return False, str(_("Aucune section de fichier trouvée."))

    return True, ""


def parse_log(content: str) -> BuildPlan:
    """Parse le contenu du journal T-E avec gestion robuste des erreurs.

    Supporte les variations de format (40/80 tirets, métadonnées optionnelles).
    """
    plan = BuildPlan()

    # Extraire les métadonnées d'en-tête
    folder_match = _SOURCE_FOLDER_RE.search(content)
    if folder_match:
        plan.original_folder = folder_match.group(1).strip()

    date_match = _DATE_RE.search(content)
    if date_match:
        plan.extraction_date = date_match.group(1).strip()

    # Extraire Format-Version (défaut 0 = legacy)
    version_match = _FORMAT_VERSION_RE.search(content)
    if version_match:
        plan.format_version = int(version_match.group(1))
    else:
        plan.format_version = 0  # Legacy v0

    # Séparer les sections
    sections = _SECTION_SPLITTER.split(content)

    for section_text in sections[1:]:  # Ignorer l'en-tête
        parsed = _parse_section(section_text)
        if parsed is not None:
            plan.add_file(parsed)

    return plan


def _parse_section(section: str) -> ParsedFile | None:
    """Parse une section de fichier unique avec robustesse accrue."""
    # Trouver la première ligne (header)
    first_nl = section.find('\n')
    if first_nl == -1:
        header = section
        rest = ''
    else:
        header = section[:first_nl].strip()
        rest = section[first_nl + 1:]

    # Parser le header : "TYPE : rel_path"
    m = _HEADER_LINE_RE.match(header)
    if not m:
        return None

    file_type = m.group(1).strip()
    rel_path = m.group(2).strip()

    if not rel_path:
        return None

    # Extraire les métadonnées optionnelles
    full_path = rel_path
    parent_dir = ''
    size_hint = ''
    line_count = 0

    fm = re.search(r"Chemin complet:\s*(.+?)\n", rest)
    if fm:
        full_path = fm.group(1).strip()

    pm = re.search(r"Dossier parent:\s*(.+?)\n", rest)
    if pm:
        parent_dir = pm.group(1).strip()

    sm = re.search(r"Taille:\s*(.+?)\n", rest)
    if sm:
        size_hint = sm.group(1).strip()

    lm = re.search(r"Nombre de lignes:\s*(\d+)", rest)
    if lm:
        line_count = int(lm.group(1))

    # Trouver le contenu après le séparateur
    sep_match = _SEPARATOR_RE.search(rest)
    if not sep_match:
        return None

    content_start = sep_match.end()

    # Trouver la fin
    end_pos = rest.find(_END_MARKER, content_start)
    if end_pos == -1:
        content = rest[content_start:]
    else:
        content = rest[content_start:end_pos]

    # Nettoyer
    content = content.rstrip('\n') + '\n'

    # Décoder .mo base64
    if file_type == 'mo' or rel_path.endswith('.mo'):
        b64_match = _MO_BASE64_RE.search(content)
        if b64_match:
            try:
                decoded = base64.b64decode(b64_match.group(1).strip())
                content = decoded.decode('latin-1', errors='replace')
            except Exception:
                logger.debug("Exception decoding base64 .mo file", exc_info=True)

    return ParsedFile(
        rel_path=rel_path,
        full_path=full_path,
        file_type=file_type,
        content=content,
        parent_dir=parent_dir,
        size_hint=size_hint,
        line_count=line_count,
    )


# ── Sécurité ────────────────────────────────────────────────────────────────

def sanitize_path(rel_path: str) -> str:
    """Nettoie un chemin de fichier pour éviter les attaques de type path traversal."""
    # Normaliser les séparateurs
    rel_path = rel_path.replace('\\', '/')
    parts = [p for p in rel_path.split('/') if p and p != '.']

    safe_parts = []
    for part in parts:
        if part == '..':
            continue
        # Caractères interdits dans les noms de fichiers Windows
        part = re.sub(r'[<>:"|?*]', '_', part)
        safe_parts.append(part)

    return '/'.join(safe_parts) if safe_parts else ''


# ── Reconstruction ──────────────────────────────────────────────────────────

def build_project(
    plan: BuildPlan,
    destination: Path,
    *,
    skip_binary: bool = True,
    skip_hidden: bool = True,
    overwrite: bool = True,
    dry_run: bool = False,
    selected_files: list[str] | None = None,
    on_progress: Any = None,
    on_log: Any = None,
) -> dict[str, Any]:
    """Reconstruit le projet à partir du plan.

    Args:
        plan: Le plan de construction extrait du journal.
        destination: Répertoire de destination.
        skip_binary: Ignorer les fichiers binaires.
        skip_hidden: Ignorer les dossiers cachés.
        overwrite: Écraser les fichiers existants.
        dry_run: Simuler sans écrire.
        selected_files: Liste des chemins à reconstruire (None = tous).
        on_progress: Callback (current, total, file_path).
        on_log: Callback (message, level).

    Returns:
        Dictionnaire de statistiques et manifest.
    """
    stats = {
        'created': 0, 'skipped': 0, 'errors': 0, 'conflicts': 0,
        'total_bytes': 0, 'dry_run': dry_run,
    }
    created_files: list[str] = []
    errors: list[tuple[str, str]] = []

    def _log(msg: str, level: str = 'info') -> None:
        if on_log:
            on_log(msg, level)

    def _progress(current: int, total: int, path: str = '') -> None:
        if on_progress:
            on_progress(current, total, path)

    # Créer la destination
    if not dry_run:
        try:
            destination.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            _log(f"Erreur création dossier destination : {exc}", 'error')
            return stats

    total = len(plan.files)
    selected_set = set(selected_files) if selected_files else None

    for i, f in enumerate(plan.files):
        _progress(i + 1, total, f.rel_path)

        # Filtrage
        if selected_set and f.rel_path not in selected_set:
            stats['skipped'] += 1
            continue

        if skip_hidden and f.is_ignored_dir:
            stats['skipped'] += 1
            continue

        if skip_binary and f.is_binary:
            stats['skipped'] += 1
            continue

        # Sécuriser le chemin
        safe = sanitize_path(f.rel_path)
        if not safe:
            _log(f"⚠ Chemin invalide ignoré : {f.rel_path}", 'warning')
            stats['skipped'] += 1
            continue

        file_path = destination / safe

        # Détection de conflits
        if file_path.exists() and not overwrite:
            stats['conflicts'] += 1
            _log(f"⚠ Conflit (existe déjà) : {safe}", 'warning')
            stats['skipped'] += 1
            continue

        if dry_run:
            stats['created'] += 1
            created_files.append(safe)
            _log(f"[DRY] Créerait : {safe}")
            continue

        # Écriture
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)

            if f.extension == '.mo' and f.content:
                try:
                    decoded = base64.b64decode(f.content)
                    file_path.write_bytes(decoded)
                    stats['total_bytes'] += len(decoded)
                except Exception:
                    file_path.write_text(f.content, encoding='utf-8', errors='replace')
                    stats['total_bytes'] += len(f.content.encode('utf-8'))
            else:
                file_path.write_text(f.content, encoding='utf-8', errors='replace')
                stats['total_bytes'] += len(f.content.encode('utf-8'))

            stats['created'] += 1
            created_files.append(safe)
            _log(f"✓ {safe}")

        except Exception as exc:
            stats['errors'] += 1
            errors.append((safe, str(exc)))
            _log(f"✗ {safe} : {exc}", 'error')
            logger.exception("Erreur création %s", file_path)

    # Écrire le manifest pour annulation
    if not dry_run and created_files:
        _write_manifest(destination, plan, created_files)

    stats['errors_list'] = errors
    stats['created_files'] = created_files
    return stats


def _write_manifest(destination: Path, plan: BuildPlan, created_files: list[str]) -> None:
    """Écrit un manifest pour permettre l'annulation."""
    manifest = {
        'version': 1,
        'original_folder': plan.original_folder,
        'extraction_date': plan.extraction_date,
        'files': created_files,
        'file_details': [f.to_dict() for f in plan.files if f.rel_path in created_files],
    }
    try:
        manifest_path = destination / _MANIFEST_NAME
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding='utf-8',
        )
    except Exception:
        logger.debug("Exception writing builder manifest", exc_info=True)


def undo_build(destination: Path) -> tuple[bool, str]:
    """Annule une reconstruction précédente via le manifest."""
    manifest_path = destination / _MANIFEST_NAME
    if not manifest_path.exists():
        return False, "Aucun manifest trouvé. Impossible d'annuler."

    try:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    except Exception as exc:
        return False, f"Erreur lecture manifest : {exc}"

    files = manifest.get('files', [])
    deleted = 0
    errors = 0

    for rel_path in files:
        file_path = destination / rel_path
        if file_path.exists():
            try:
                file_path.unlink()
                deleted += 1
            except Exception:
                errors += 1
                logger.debug("Exception deleting file %s during undo", rel_path, exc_info=True)

    # Supprimer les dossiers vides
    for dirpath in sorted(destination.rglob('*'), reverse=True):
        if dirpath.is_dir() and not any(dirpath.iterdir()):
            try:
                dirpath.rmdir()
            except Exception:
                logger.debug("Exception removing empty directory %s during undo", dirpath, exc_info=True)

    # Supprimer le manifest
    try:
        manifest_path.unlink()
    except Exception:
        logger.debug("Exception deleting manifest file during undo", exc_info=True)

    return True, f"{deleted} fichiers supprimés, {errors} erreurs."


# ── Vue GUI ─────────────────────────────────────────────────────────────────

def build_builder_view(shell) -> ttk.Frame:
    """Construit la vue Builder dans le workspace."""
    frame = ttk.Frame(shell.workspace, padding=12)
    frame.columnconfigure(0, weight=1)

    # ── Journal T-E ──
    log_frame = ttk.Frame(frame)
    log_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 8))
    log_frame.columnconfigure(1, weight=1)

    ttk.Label(log_frame, text=str(_("Journal T-E :"))).grid(
        row=0, column=0, sticky=tk.W, padx=(0, 6))
    log_var = tk.StringVar()
    ttk.Entry(log_frame, textvariable=log_var, state='readonly').grid(
        row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 6))
    browse_log_btn = ttk.Button(log_frame, text="...", width=3)
    browse_log_btn.grid(row=0, column=2)

    # ── Destination ──
    dst_frame = ttk.Frame(frame)
    dst_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 8))
    dst_frame.columnconfigure(1, weight=1)

    ttk.Label(dst_frame, text=str(_("Destination :"))).grid(
        row=0, column=0, sticky=tk.W, padx=(0, 6))
    dst_var = tk.StringVar()
    ttk.Entry(dst_frame, textvariable=dst_var, state='readonly').grid(
        row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 6))
    browse_dst_btn = ttk.Button(dst_frame, text="...", width=3)
    browse_dst_btn.grid(row=0, column=2)

    # ── Options ──
    opts_frame = ttk.LabelFrame(frame, text=str(_("Options")), padding=8)
    opts_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 8))

    skip_binary_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(
        opts_frame,
        text=str(_("Ignorer les fichiers binaires (images, vidéos, etc.)")),
        variable=skip_binary_var,
    ).grid(row=0, column=0, sticky=tk.W)

    skip_hidden_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(
        opts_frame,
        text=str(_("Ignorer les dossiers cachés (.git, __pycache__, etc.)")),
        variable=skip_hidden_var,
    ).grid(row=1, column=0, sticky=tk.W)

    overwrite_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(
        opts_frame,
        text=str(_("Écraser les fichiers existants")),
        variable=overwrite_var,
    ).grid(row=2, column=0, sticky=tk.W)

    dry_run_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(
        opts_frame,
        text=str(_("Mode simulation (dry-run) — ne rien écrire")),
        variable=dry_run_var,
    ).grid(row=3, column=0, sticky=tk.W)

    # ── Barre de progression ──
    progress_var = tk.DoubleVar(value=0)
    progress_bar = ttk.Progressbar(frame, variable=progress_var, maximum=100)
    progress_bar.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(4, 4))

    status_var = tk.StringVar(value=str(_("Sélectionnez un journal T-E.")))
    ttk.Label(frame, textvariable=status_var, wraplength=600).grid(
        row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 8))

    # ── Boutons ──
    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(0, 8))

    build_btn = ttk.Button(btn_frame, text=str(_("Construire")),
                           style='Accent.TButton', state='disabled')
    build_btn.pack(side=tk.LEFT, padx=(0, 4))

    dry_btn = ttk.Button(btn_frame, text=str(_("Simuler")), state='disabled')
    dry_btn.pack(side=tk.LEFT, padx=(0, 4))

    preview_btn = ttk.Button(btn_frame, text=str(_("Aperçu")), state='disabled')
    preview_btn.pack(side=tk.LEFT, padx=(0, 4))

    undo_btn = ttk.Button(btn_frame, text=str(_("Annuler")))
    undo_btn.pack(side=tk.LEFT)

    # ── Zone de log ──
    log_output_frame = ttk.Frame(frame, style='Card.TFrame', padding=(10, 6))
    log_output_frame.grid(row=6, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
    frame.rowconfigure(6, weight=1)
    log_output_frame.columnconfigure(0, weight=1)
    log_output_frame.rowconfigure(0, weight=1)

    log_text = tk.Text(
        log_output_frame, height=12, wrap=tk.WORD,
        bg='#1B2027', fg='#E7EBF0', insertbackground='#E7EBF0',
        font=('Consolas', 9), bd=0, highlightthickness=0,
    )
    log_scroll = ttk.Scrollbar(log_output_frame, orient=tk.VERTICAL, command=log_text.yview)
    log_text.configure(yscrollcommand=log_scroll.set)
    log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    log_text.configure(state='disabled')

    # ── État interne ──
    state: dict[str, Any] = {
        'plan': None,
        'destination': None,
    }

    # ── Fonctions utilitaires ──

    def _log(msg: str) -> None:
        log_text.configure(state='normal')
        log_text.insert(tk.END, msg + "\n")
        log_text.see(tk.END)
        log_text.configure(state='disabled')

    def _clear_log() -> None:
        log_text.configure(state='normal')
        log_text.delete('1.0', tk.END)
        log_text.configure(state='disabled')

    def _check_ready() -> None:
        ready = bool(log_var.get() and dst_var.get() and state['plan'])
        build_btn.config(state='normal' if ready else 'disabled')
        dry_btn.config(state='normal' if ready else 'disabled')
        preview_btn.config(state='normal' if state['plan'] else 'disabled')

    def _on_progress(current: int, total: int, path: str) -> None:
        pct = current / total * 100 if total > 0 else 100
        progress_var.set(pct)
        status_var.set(f"{current}/{total} — {Path(path).name}" if path else f"{current}/{total}")

    def _on_log_msg(msg: str, level: str = 'info') -> None:
        _log(msg)

    # ── Actions ──

    def _browse_log() -> None:
        path = filedialog.askopenfilename(
            title=str(_("Sélectionner un journal T-E")),
            filetypes=[("Fichiers texte", "*.txt"), ("Tous les fichiers", "*.*")])
        if not path:
            return

        log_var.set(path)
        _clear_log()

        try:
            content = Path(path).read_text(encoding='utf-8', errors='replace')
        except Exception as exc:
            messagebox.showerror(str(_("Erreur")), str(exc))
            return

        # Validation
        valid, err_msg = validate_log(content)
        if not valid:
            _log(f"✗ {err_msg}")
            status_var.set(str(_("Journal invalide.")))
            return

        plan = parse_log(content)
        state['plan'] = plan

        _log(f"✓ Journal chargé : {plan.total_files} fichiers trouvés.")
        _log(
            f"  Texte : {plan.text_count}  |  "
            f"Binaires : {plan.binary_count}  |  "
            f"Ignorés : {plan.ignored_count}"
        )
        if plan.original_folder:
            _log(f"  Source : {plan.original_folder}")
        if plan.extraction_date:
            _log(f"  Date : {plan.extraction_date}")

        build_btn.config(state='normal')
        dry_btn.config(state='normal')
        preview_btn.config(state='normal')
        _check_ready()

    def _browse_dst() -> None:
        path = filedialog.askdirectory(title=str(_("Sélectionner la destination")))
        if path:
            dst_var.set(path)
            state['destination'] = Path(path)
            _check_ready()

    def _do_build(dry_run: bool = False) -> None:
        plan = state['plan']
        dest = state['destination']
        if not plan or not dest:
            return

        build_btn.config(state='disabled')
        dry_btn.config(state='disabled')
        preview_btn.config(state='disabled')
        progress_var.set(0)
        _clear_log()

        if dry_run:
            _log("═══ SIMULATION (dry-run) ═══\n")

        def run() -> None:
            def on_progress(cur, total, path):
                safe_after(frame, 0, lambda: _on_progress(cur, total, path))

            def on_log_msg(msg, level='info'):
                safe_after(frame, 0, lambda: _log(msg))

            stats = build_project(
                plan, dest,
                skip_binary=skip_binary_var.get(),
                skip_hidden=skip_hidden_var.get(),
                overwrite=overwrite_var.get(),
                dry_run=dry_run,
                on_progress=on_progress,
                on_log=on_log_msg,
            )

            def finish() -> None:
                progress_var.set(100)
                mode = " [SIMULATION]" if dry_run else ""
                status_var.set(
                    f"{stats['created']} créés, {stats['skipped']} ignorés, "
                    f"{stats['errors']} erreurs{mode}"
                )
                _log(f"\n═══ Terminé{mode} : {stats['created']} fichiers ═══")
                if stats.get('errors_list'):
                    _log("\nErreurs :")
                    for path, err in stats['errors_list']:
                        _log(f"  ✗ {path} : {err}")
                build_btn.config(state='normal')
                dry_btn.config(state='normal')
                preview_btn.config(state='normal')

            safe_after(frame, 0, finish)

        Thread(target=run, daemon=True).start()

    def _preview() -> None:
        plan = state['plan']
        if not plan:
            return

        win = tk.Toplevel(frame)
        win.title(str(_("Aperçu de la reconstruction")))
        win.geometry("700x500")

        # En-tête
        hdr = ttk.Frame(win, padding=10)
        hdr.pack(fill=tk.X)
        info_text = (
            f"Source : {plan.original_folder or 'N/A'}  |  "
            f"Date : {plan.extraction_date or 'N/A'}  |  "
            f"Total : {plan.total_files} fichiers"
        )
        ttk.Label(hdr, text=info_text, font=('Segoe UI', 10)).pack(anchor=tk.W)

        # Arbre
        tree_frame = ttk.Frame(win)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10)

        tree = ttk.Treeview(
            tree_frame, columns=('type', 'size', 'status'),
            show='tree headings', selectmode='extended',
        )
        tree.heading('#0', text="Fichier")
        tree.heading('type', text="Type")
        tree.heading('size', text="Taille")
        tree.heading('status', text="Statut")
        tree.column('#0', width=300)
        tree.column('type', width=60)
        tree.column('size', width=80)
        tree.column('status', width=120)

        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        skip_b = skip_binary_var.get()
        skip_h = skip_hidden_var.get()

        for f in plan.files:
            if skip_h and f.is_ignored_dir:
                status = str(_("ignoré (dossier)"))
                tag = 'ignored'
            elif skip_b and f.is_binary:
                status = str(_("ignoré (binaire)"))
                tag = 'ignored'
            else:
                status = str(_("à créer"))
                tag = 'ok'

            size = f.size_hint or f"{f.size_bytes}"
            tree.insert('', 'end', text=f.rel_path,
                        values=(f.file_type, size, status), tags=(tag,))

        tree.tag_configure('ok', foreground='#4EC9B0')
        tree.tag_configure('ignored', foreground='#888888')

        # Boutons
        btn = ttk.Frame(win, padding=10)
        btn.pack(fill=tk.X)
        ttk.Button(btn, text=str(_("Fermer")), command=win.destroy).pack(side=tk.RIGHT)

    def _undo() -> None:
        dest = state['destination']
        if not dest:
            messagebox.showwarning(
                str(_("Destination requise")),
                str(_("Sélectionnez un dossier de destination pour annuler.")))
            return

        if not (dest / _MANIFEST_NAME).exists():
            messagebox.showinfo(
                str(_("Annulation")),
                str(_("Aucun manifest trouvé dans ce dossier.\n"
                      "Seules les reconstructions récentes peuvent être annulées.")))
            return

        confirm = messagebox.askyesno(
            str(_("Annuler la reconstruction")),
            str(_("Supprimer tous les fichiers créés par Builder dans :\n{dest}?").format(
                dest=str(dest))),
            icon='warning',
        )
        if not confirm:
            return

        ok, msg = undo_build(dest)
        if ok:
            messagebox.showinfo(str(_("Annulation")), msg)
            _log(f"✓ Annulation : {msg}")
        else:
            messagebox.showerror(str(_("Erreur")), msg)


    # ── Connexions ──
    # Assignation directe des commandes aux boutons (références directes)
    browse_log_btn.config(command=_browse_log)
    browse_dst_btn.config(command=_browse_dst)

    build_btn.config(command=lambda: _do_build(dry_run=False))
    dry_btn.config(command=lambda: _do_build(dry_run=True))
    preview_btn.config(command=_preview)
    undo_btn.config(command=_undo)

    return frame


# ── Enregistrement ──────────────────────────────────────────────────────────

TOOL = Tool(
    id='builder',
    name="Façonneur",
    description="Reconstituez un projet à partir d'un journal T-E.",
    category="Extraction",
    icon='⚒️',
    shortcut='Ctrl+Shift+B',
    view=build_builder_view,
    keywords=('builder', 'reconstruire', 'reconstituer', 'projet', 'export', 'log', 'façonner'),
    order=2,
)


def register(reg, cmds) -> None:
    reg.register(TOOL)
    cmds.register(Command(
        id='tool.builder',
        label="Façonneur",
        description="Reconstituer un projet à partir d'un journal T-E",
        shortcut='Ctrl+Shift+B',
        icon='⚒️',
        tool_id='builder',
        keywords=('builder', 'reconstruire', 'reconstituer', 'projet', 'façonner'),
    ))

# scripts/repro_duplication.py
"""FORENSIC AUDIT - Partie 2 : reproduction du bug sur un dossier "piégé".

Crée un dossier temporaire contenant des pièges classiques
(.pytest_cache, __pycache__, logs, junctions/symlinks en boucle),
puis lance l'extraction T-E via l'API publique et mesure le résultat.

Usage :  python scripts/repro_duplication.py
Ne corrige RIEN : audit pur.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Permet l'exécution depuis la racine du projet
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Active les compteurs debug pour le script de repro
os.environ['TE_DEBUG_COUNTERS'] = '1'

from src.config import ExtractionOptions                      # noqa: E402
from src.extractor.context import ExtractionContext            # noqa: E402
from src.extractor.engine import ExtractionEngine, SUCCESS     # noqa: E402
from src.extractor.file_discovery import _DEBUG_COUNTERS as _GLOBAL_COUNTER  # noqa: E402


# --------------------------------------------------------------------------- #
# 2.1 Construction du dossier piégé
# --------------------------------------------------------------------------- #

def _make_junction(link: Path, target: Path) -> str:
    """Crée une junction Windows (pas de privilège admin requis).
    Replie sur os.symlink puis sur un simple répertoire en dernier recours."""
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        if os.name == 'nt':
            proc = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(target)],
                check=False, capture_output=True, text=True,
            )
            if proc.returncode == 0:
                return "junction"
            # mklink échoue si la cible est déjà un lien ou si droits insuffisants
            if link.exists() or link.is_symlink():
                try:
                    if link.is_dir() and not link.is_symlink():
                        shutil.rmtree(link)
                    else:
                        link.unlink()
                except OSError:
                    pass
            try:
                os.symlink(str(target), str(link), target_is_directory=True)
                return "symlink"
            except OSError:
                return "none"
        else:
            os.symlink(str(target), str(link), target_is_directory=True)
            return "symlink"
    except Exception as e:  # pragma: no cover
        print(f"  [!] Impossible de créer le lien {link.name} : {e}")
        return "none"


def build_trap_folder(root: Path) -> dict:
    """Crée le dossier piégé et retourne un dict d'infos de création."""
    root.mkdir(parents=True, exist_ok=True)
    info: dict = {}

    # --- un fichier real.py normal ---------------------------------------- #
    (root / "real.py").write_text(
        "def hello():\n    return 'world'\n" + "# padding\n" * 50,
        encoding='utf-8',
    )
    info['real.py'] = (root / "real.py").stat().st_size

    # --- .pytest_cache/v/cache/nodeids (100 lignes de chemins fictifs) ---- #
    cache = root / ".pytest_cache" / "v" / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    nodeids_lines = [
        f"tests/unit/test_fictif_{i:03d}.py::test_case_{i:03d}::test_interne"
        for i in range(100)
    ]
    (cache / "nodeids").write_text("\n".join(nodeids_lines), encoding='utf-8')
    (cache / "lastfailed").write_text('{"tests/unit/test_x.py::test_y": 1}', encoding='utf-8')
    (cache / "CACHEDIR.TAG").write_text("Signature: 8a477f597d28d172789f06886806bc55", encoding='utf-8')
    info['nodeids_lines'] = len(nodeids_lines)

    # --- __pycache__ avec 5 .pyc vides ------------------------------------ #
    pyc_dir = root / "__pycache__"
    pyc_dir.mkdir(parents=True, exist_ok=True)
    for i in range(5):
        (pyc_dir / f"module_{i}.cpython-311.pyc").write_bytes(b"")
    info['pyc_count'] = 5

    # --- logs/tllm.log de 1 Mo ------------------------------------------- #
    logs = root / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    log_line = "2026-09-26 12:00:00 INFO [TLLM] processing request id=12345 path=C:\\Dossier tlf\\code\\TLLMv6\n"
    reps = max(1, (1024 * 1024) // len(log_line))
    (logs / "tllm.log").write_text(log_line * reps, encoding='utf-8')
    info['tllm.log'] = (logs / "tllm.log").stat().st_size

    # --- symlink loop -> "." (le dossier lui-même) ------------------------ #
    info['loop'] = _make_junction(root / "loop", root)

    # --- symlink parent_link -> ".." -------------------------------------- #
    info['parent_link'] = _make_junction(root / "parent_link", root.parent)

    return info


# --------------------------------------------------------------------------- #
# 2.2 Lancement de l'extraction via l'API publique
# --------------------------------------------------------------------------- #

def run_extraction(folder: Path, out_file: Path) -> dict:
    """Lance l'extraction via ExtractionEngine (API publique T-E)."""
    options = ExtractionOptions()  # options par défaut = configuration GUI standard
    context = ExtractionContext(
        folder_path=folder,
        options=options,
        output_path=out_file,
        selected_files=None,
    )
    engine = ExtractionEngine(context)

    t0 = time.monotonic()
    result = engine.run(progress_callback=None, log_callback=None)
    duration = time.monotonic() - t0

    return {
        'result': result,
        'duration': duration,
        'context': context,
    }


# --------------------------------------------------------------------------- #
# 2.3 Mesures
# --------------------------------------------------------------------------- #

def measure_output(out_file: Path) -> dict:
    """Compte les occurrences des marqueurs dans l'output."""
    markers = ['real.py', '.pytest_cache', '__pycache__', 'loop', 'parent_link']
    counts = {m: 0 for m in markers}
    total_lines = 0
    # Lecture par blocs pour ne pas charger 792 Mo en RAM si le bug se reproduit
    if not out_file.exists():
        return {'counts': counts, 'total_lines': 0, 'size': 0}
    size = out_file.stat().st_size
    buf = ''
    with open(out_file, 'r', encoding='utf-8', errors='replace') as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), ''):
            buf += chunk
            total_lines += chunk.count('\n')
            for m in markers:
                counts[m] += buf.count(m)
            # garder le buffer borné (chevauchement pour les tokens coupés)
            keep = max(len(m) for m in markers)
            buf = buf[-keep:] if len(buf) > keep else buf
        for m in markers:
            counts[m] += buf.count(m)
    return {'counts': counts, 'total_lines': total_lines, 'size': size}


def raw_walk_measure(root: Path, cap: int = 400) -> dict:
    """Mesure le fan-out réel (Partie 6) sur le dossier, sans extraction.

    ATTENTION : un dossier contenant une junction auto-référente produit une
    traversée INFINIE. Un 'cap' est appliqué et signalé pour rester exécutable.
    """
    total_dirs = 0
    total_files = 0
    total_bytes = 0
    deepest = 0
    levels = 0
    truncated = False
    for r, dirs, files in os.walk(root, followlinks=False):
        levels += 1
        if levels > cap:
            truncated = True
            break
        total_dirs += len(dirs)
        total_files += len(files)
        try:
            depth = len(Path(r).relative_to(root).parts)
        except ValueError:
            depth = 0
        deepest = max(deepest, depth)
        for f in files:
            try:
                total_bytes += (Path(r) / f).stat().st_size
            except OSError:
                pass
    return {'dirs': total_dirs, 'files': total_files,
            'bytes': total_bytes, 'deepest': deepest,
            'levels': levels, 'truncated': truncated}


# --------------------------------------------------------------------------- #
# 2.4 Rapport
# --------------------------------------------------------------------------- #

def human(n: float) -> str:
    for unit in ('o', 'Ko', 'Mo', 'Go'):
        if n < 1024:
            return f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} To"


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="te_repro_"))
    trap = tmp / "trap"
    out_file = tmp / "repro_output.txt"

    print("=" * 70)
    print("PARTIE 2 — REPRODUCTION SUR DOSSIER PIEGE")
    print("=" * 70)
    print(f"Dossier de travail : {trap}")
    print()

    print("[2.1] Construction du dossier piege...")
    info = build_trap_folder(trap)
    print(f"  real.py           : {info['real.py']} octets")
    print(f"  nodeids           : {info['nodeids_lines']} lignes")
    print(f"  __pycache__/*.pyc : {info['pyc_count']}")
    print(f"  logs/tllm.log     : {info['tllm.log']} octets ({human(info['tllm.log'])})")
    print(f"  lien 'loop'       : {info['loop']}")
    print(f"  lien 'parent_link': {info['parent_link']}")
    print()

    print("[6.1] Fan-out reel du dossier source (os.walk brut, cap 400 niveaux) :")
    # NOTE : lance AVANT l'extraction mais avec cap, car une junction
    # auto-référente rend os.walk(followlinks=False) non borné sur Windows.
    fan = raw_walk_measure(trap, cap=400)
    trunc_note = "  [!!] TRAVERSÉE NON BORNÉE (tronquée au cap)" if fan['truncated'] else ""
    print(f"  dirs={fan['dirs']} files={fan['files']} "
          f"bytes={fan['bytes']} ({human(fan['bytes'])}) deepest={fan['deepest']} "
          f"levels={fan['levels']}{trunc_note}")
    print()

    print("[2.2] Lancement de l'extraction (ExtractionEngine)...")
    # Remettre les compteurs à zéro
    for k in _GLOBAL_COUNTER:
        _GLOBAL_COUNTER[k] = 0
    t_start = time.monotonic()
    run = run_extraction(trap, out_file)
    print(f"  resultat   : {run['result']} (SUCCESS={SUCCESS!r})")
    print(f"  duree      : {run['duration']:.2f} s")
    print(f"  compteurs  : {_GLOBAL_COUNTER}")
    print()

    print("[2.3] Mesure de l'output...")
    m = measure_output(out_file)
    print()

    print("=" * 70)
    print("| Metrique                    | Valeur                |")
    print("|-----------------------------|-----------------------|")
    print(f"| Taille output               | {human(m['size'])} ({m['size']} o) |")
    for k, v in m['counts'].items():
        print(f"| Occurrences {k:<14} | {v:<20} |")
    print(f"| Nombre total de lignes      | {m['total_lines']:<20} |")
    print(f"| Fan-out source (octets)     | {human(fan['bytes']):<20} |")
    print(f"| Niveaux parcourus (brut)    | {fan['levels']:<20} |")
    print(f"| Duree extraction            | {run['duration']:.2f} s{'':<11} |")
    print("=" * 70)

    print()
    verdict = "BUG REPRODUIT : OUI" if m['size'] > 10 * 1024 * 1024 else "BUG REPRODUIT : NON"
    print(f"VERDICT : {verdict}  (seuil = 10 Mo, output = {human(m['size'])})")

    # Analyse des occurrences
    print()
    print("Analyse des marqueurs :")
    for k, v in m['counts'].items():
        flag = ""
        if k in ('.pytest_cache', '__pycache__') and v > 0:
            flag = "  <-- FICHIER TECHNIQUE NON FILTRE"
        if k in ('loop', 'parent_link') and v > 5:
            flag = "  <-- BOUCLE/JUNCTION DUPLIQUEE"
        if k == 'real.py' and v > 50:
            flag = "  <-- DUPLICATION QUADRATIQUE SUSPECTEE"
        print(f"  {k:<16} = {v:<8}{flag}")

    # Conservation ou nettoyage
    keep = "--keep" in sys.argv
    if keep:
        print()
        print(f"[!] Artefacts conserves dans : {tmp}")
    else:
        _force_remove(trap)
        _force_remove(out_file)
        try:
            tmp.rmdir()
        except OSError:
            pass
        print()
        print("[i] Artefacts supprimes (utiliser --keep pour les conserver)")

    return 0 if m['size'] > 10 * 1024 * 1024 else 0


def _force_remove(p: Path) -> None:
    """Supprime un chemin en gérant les junctions (sans suivre les liens)."""
    import stat
    try:
        if not p.exists() and not p.is_symlink():
            return
        if p.is_dir() and not p.is_symlink():
            def onerror(func, path, exc):
                try:
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
                except OSError:
                    pass
            shutil.rmtree(p, onerror=onerror)
        else:
            p.unlink()
    except OSError as e:
        print(f"  [!] Suppression impossible {p} : {e}")


if __name__ == '__main__':
    raise SystemExit(main())

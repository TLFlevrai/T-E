# scripts/_probe_links.py - FORENSIC AUDIT: Windows junction semantics probe
import os
import stat
import sys
from pathlib import Path

REPARSE = getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400)


def probe(root: Path, label: str, max_levels: int = 6):
    print(f"=== {label} : {root} ===")
    for x in (root / 'loop', root / 'parent_link'):
        if not (x.exists() or x.is_symlink()):
            print(f"  {x.name}: ABSENT")
            continue
        st = os.lstat(str(x))
        attrs = getattr(st, 'st_file_attributes', 0)
        print(f"  {x.name}: is_symlink={x.is_symlink()} "
              f"reparse={bool(attrs & REPARSE)} "
              f"isdir_follows=True/False? "
              f"st_mode_dir={stat.S_ISDIR(st.st_mode)}")
    print("  --- os.walk(followlinks=False) ---")
    levels = 0
    for r, dirs, files in os.walk(root, followlinks=False):
        rel = Path(r).relative_to(root)
        print(f"    depth={len(rel.parts)} rel={rel} dirs={dirs} nfiles={len(files)}")
        levels += 1
        if levels > max_levels:
            print("    ... (arrêt: cap d'observation atteint)")
            break
    print()


if __name__ == '__main__':
    trap = Path(sys.argv[1])
    probe(trap, "DOSSIER PIEGE")

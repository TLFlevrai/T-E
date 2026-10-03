# extract_messages.py
"""Extrait les messages traduisibles vers locale/messages.pot.

Équivalent pybabel extract, mais piloté par pyproject.toml ([tool.babel])
pour éviter de dupliquer la configuration dans un babel.cfg.
"""
import subprocess
import sys
from pathlib import Path

PYPROJECT = Path("pyproject.toml")


def _pybabel_command() -> list[str]:
    """Commande d'extraction lue depuis [tool.babel] de pyproject.toml."""
    try:
        import tomllib
    except ModuleNotFoundError:  # Python < 3.11
        import tomli as tomllib  # type: ignore[no-redef]

    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    babel_cfg = data.get("tool", {}).get("babel", {})
    if not babel_cfg:
        sys.exit("[tool.babel] introuvable dans pyproject.toml")

    mapping = babel_cfg.get("mappings", {})
    ext = next(iter(mapping), ".py")
    extractor = mapping.get(ext, {}).get("extractor", "python")

    cmd = ["pybabel", "extract", "--input-dirs", ",".join(babel_cfg["input_dirs"])]
    if extractor and extractor != "python":
        cmd += ["--extractor", extractor]
    for ext_name, kwargs in mapping.items():
        # -F attend un fichier de mapping, pas une paire ext=extracteur.
        # Un mapping n'est utile que si l'extracteur n'est pas celui par
        # défaut (python) : ici il ne l'est pas, on omet donc -F.
        if kwargs.get("extractor", "python") not in ("python", None):
            cmd += ["--extractor", kwargs["extractor"]]
    # --sort-by-file et --sort-output sont mutuellement exclusifs chez
    # pybabel ; le catalogue existant est trié par fichier (convention
    # du dépôt, cf. sort_by_file dans pyproject.toml).
    cmd += [
        "--output", babel_cfg["output_file"],
        "--project", babel_cfg["project"],
        "--version", babel_cfg["version"],
        "--sort-by-file",
    ]
    return cmd


def main() -> int:
    cmd = _pybabel_command()
    print("+", " ".join(cmd))
    try:
        return subprocess.call(cmd)
    except FileNotFoundError:
        sys.exit("pybabel introuvable : `pip install babel`")


if __name__ == "__main__":
    sys.exit(main())

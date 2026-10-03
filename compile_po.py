# compile_po.py
"""Synchronise et compile les catalogues de traduction.

- `messages.pot` est la source (extrait via `extract_messages.py`).
- Chaque `locale/<lang>/LC_MESSAGES/messages.po` reçoit UNIQUEMENT les
  messages absents : une traduction deja ecrite n'est jamais ecrassee.
- Compilation `.po` -> `.mo`.
"""
import polib
from pathlib import Path

LANGUAGES = ("fr", "en")
POT_FILE = Path("locale/messages.pot")


def _out(message: str) -> None:
    """print() tolerant a l'encodage de la console (Windows/cp1252)."""
    print(message.encode("ascii", "replace").decode("ascii"))


def ensure_locale_structure():
    """Cree les dossiers et fichiers .po s'ils n'existent pas."""
    locale_dir = Path("locale")
    for lang in LANGUAGES:
        po_dir = locale_dir / lang / "LC_MESSAGES"
        po_dir.mkdir(parents=True, exist_ok=True)
        po_file = po_dir / "messages.po"

        if not po_file.exists():
            # Cree un fichier .po minimal avec en-tete
            po_content = f'''msgid ""
msgstr ""
"Project-Id-Version: PythonCodeExtractor 1.0\\n"
"POT-Creation-Date: 2026-08-13 11:00+0200\\n"
"PO-Revision-Date: 2026-08-13 11:00+0200\\n"
"Last-Translator: \\n"
"Language-Team: \\n"
"Language: {lang}\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
'''
            po_file.write_text(po_content, encoding="utf-8")
            _out(f"OK. Fichier {po_file} cree.")


def _find_entry(po, entry):
    """Retrouve une entree existante a partir d'un message du .pot."""
    for candidate in po:
        if candidate.msgid == entry.msgid and candidate.msgctxt == entry.msgctxt:
            return candidate
    return None


def merge_pot_into_po():
    """Ajoute au .po de chaque langue les messages absents du .pot.

    Les msgid existants gardent leur msgstr. Aucun message traduit n'est
    ecrase : le catalogue merge est une union, ce qui evite de perdre le
    travail de traduction a chaque regeneration du .pot.
    """
    if not POT_FILE.exists():
        _out("WARN  locale/messages.pot absent - rien a fusionner.")
        return

    pot = polib.pofile(str(POT_FILE))
    total_added = 0

    for lang in LANGUAGES:
        po_path = Path("locale") / lang / "LC_MESSAGES" / "messages.po"
        if not po_path.exists():
            continue
        po = polib.pofile(str(po_path))
        before = len(po)

        for entry in pot:
            existing = _find_entry(po, entry)
            if existing is not None:
                # msgid identique : msgstr conserve tel quel.
                continue
            po.append(polib.POEntry(
                msgctxt=entry.msgctxt,
                msgid=entry.msgid,
                msgstr=entry.msgstr if entry.msgstr else "",
                occurrences=entry.occurrences,
            ))

        po.save(str(po_path))
        added = len(po) - before
        total_added += added
        if added:
            _out(f"OK. {added} message(s) ajoute(s) a {po_path}")

    _out(f"Fusion terminee : {total_added} message(s) ajoute(s).")


def compile_all_po():
    """Compile tous les fichiers .po en .mo.

    Les .po ne sont PAS reecrits : polib retirerait au passage les entrees
    obsoletes `#~`, ce qui detruirait l'historique de traduction. Seuls les
    .mo sont regeneres.
    """
    locale_dir = Path("locale")
    if not locale_dir.exists():
        _out("Le dossier 'locale' n'existe pas. Creation...")
        ensure_locale_structure()

    for lang_dir in locale_dir.iterdir():
        if not lang_dir.is_dir():
            continue
        po_file = lang_dir / "LC_MESSAGES" / "messages.po"
        mo_file = lang_dir / "LC_MESSAGES" / "messages.mo"
        if not po_file.exists():
            _out(f"WARN  {po_file} manquant, ignore.")
            continue
        try:
            po = polib.pofile(str(po_file))
            po.save_as_mofile(str(mo_file))
            _out(f"OK. {mo_file} genere avec succes")
        except Exception as e:
            _out(f"Erreur pour {po_file} : {e}")


if __name__ == "__main__":
    ensure_locale_structure()
    merge_pot_into_po()
    compile_all_po()
    _out("Compilation terminee.")

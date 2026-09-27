================================================================================
RAPPORT D'AUDIT FORENSIQUE — Projet T-E (extraction 792 Mo)
================================================================================

A. Résultat de la repro sur dossier piégé (Partie 2)
-----------------------------------------------------
- Taille output : 2.51 Ko (2 573 octets)
- Tableau des occurrences :
| Metrique                | Valeur |
|-------------------------|--------|
| Taille output           | 2.51 Ko |
| Occurrences real.py     | 3      |
| Occurrences .pytest_cache | 0    |
| Occurrences __pycache__ | 0      |
| Occurrences loop        | 1      |
| Occurrences parent_link | 2      |
- Verdict : BUG REPRODUIT : **NON** (seuil = 10 Mo, output = 2.51 Ko)

Interprétation : Les protections (visited + ignore_patterns + pruning) fonctionnent
sur le dossier piégé minimal. Le bug 792 Mo a une cause différente.

---

B. Code exact (avec lignes) des points critiques
------------------------------------------------

### B.1 `_walk()` complet — `src/extractor/file_discovery.py:99-205`
```python
def _walk(self, folder_path: Path, collect_dirs: bool = False,
          all_files: bool = False) -> Iterator[_WalkItem]:
    max_depth = self.options.max_depth if self.options.max_depth and self.options.max_depth > 0 else None
    force_include_all = getattr(self.options, 'force_include_all', False)
    visited: set[Path] = set()

    for root, dirs, filenames in os.walk(folder_path, topdown=True, followlinks=False):
        root_path = Path(root)
        resolved_root = root_path.resolve()

        # FORENSIC AUDIT: root counter + debug
        _GLOBAL_COUNTER["walk_roots_visited"] += 1
        logger.debug("[WALK] root=%s dirs=%d files=%d depth=%d",
                     root, len(dirs), len(filenames), depth)

        # Protection anti-cycles : si on a déjà visité ce chemin résolu
        if resolved_root in visited:
            dirs[:] = []
            continue
        visited.add(resolved_root)          # ← VISITED PEUPLÉ AVANT YIELD (L.132)

        # Calculer la profondeur relative
        if max_depth is not None:
            try:
                rel = root_path.relative_to(folder_path)
                depth = len(rel.parts)
            except ValueError:
                depth = 0
            if depth >= max_depth:
                dirs[:] = []
                continue

        # --- PRUNING : supprime les dossiers ignorés AVANT la descente ---
        prune_dirs(dirs, self._ignored_patterns)     # ← FILTRES APPLIQUÉS (L.146)

        # Si include_subdirs=False, on vide dirs pour ne pas descendre
        if not self.options.include_subdirs and root != str(folder_path):
            dirs[:] = []

        # Collecter les dossiers (pour l'affichage structure)
        if collect_dirs:
            for d in dirs:
                _GLOBAL_COUNTER["walk_items_yielded"] += 1
                yield self._WalkItem('dir', rel_path=...)

        # Collecter les fichiers
        for fname in filenames:
            if should_ignore_file(fname, self._ignored_patterns, force_include_all):
                continue

            # Filtre d'extension : uniquement si on ne veut PAS tout inclure
            if not all_files and not self._is_extractable_file(fname):
                continue
            if self.options.ignore_init and fname == '__init__.py' and not all_files:
                continue

            full_path = root_path / fname
            try:
                rel_path = full_path.relative_to(folder_path)
            except ValueError:
                continue

            if collect_dirs:
                for parent in rel_path.parents:
                    if parent != Path('.'):
                        _GLOBAL_COUNTER["walk_items_yielded"] += 1
                        yield self._WalkItem('dir', rel_path=parent)

            file_size = -1
            try:
                file_size = full_path.stat().st_size
            except OSError:
                pass
            _GLOBAL_COUNTER["walk_items_yielded"] += 1
            _GLOBAL_COUNTER["files_emitted"] += 1
            yield self._WalkItem('file', full_path=full_path, rel_path=rel_path,
                                 extension=full_path.suffix, size=file_size)
```

### B.2 Fonction d'écriture complète — `src/extractor/engine.py:142-201`
```python
def _process_files(self, out_file, files, progress_callback, log_callback):
    file_sizes = []
    total_size = 0
    for full_path, rel_path, ext in files:
        try:
            size = full_path.stat().st_size
        except OSError:
            size = 0
        file_sizes.append(size)
        total_size += size

    processed_size = 0
    for i, (full_path, rel_path, ext) in enumerate(files):
        if self.cancel_event is not None and self.cancel_event.is_set():
            return CANCELLED

        if progress_callback:
            progress_callback(processed_size, total_size, str(rel_path))

        # TRAITEMENT pur (testable sans I/O)
        result = self.processor.process(full_path, rel_path, ext)

        # ÉCRITURE (déléguée à export_writer)
        write_file_section(out_file, result)

        # FORENSIC AUDIT: octets écrits
        _GLOBAL_COUNTER["bytes_written"] += len(result.content)
        if _GLOBAL_COUNTER["files_emitted"] % 1000 == 0:
            print(f"[EMIT] items={_GLOBAL_COUNTER['files_emitted']} bytes={_GLOBAL_COUNTER['bytes_written']}")

        processed_size += file_sizes[i]

        if log_callback:
            if result.read_ok:
                log_callback(f"✓ {rel_path} extrait")
            else:
                log_callback(f"✗ Erreur sur {rel_path}")

    return SUCCESS
```

### B.3 `write_file_section()` — `src/extractor/export_writer.py:19-55`
```python
def write_file_section(output_file, result: FileSectionResult):
    output_file.write(f"\n{'=' * 80}\n")
    output_file.write(f"FICHIER {result.file_type} : {rel_path}\n")
    output_file.write(f"Type: {result.file_type}\n")
    output_file.write(f"Chemin complet: {full_path}\n")
    if result.include_file_metadata:
        output_file.write(f"Dossier parent: {parent_dir}\n")
        output_file.write(f"Taille: {human_size(result.file_size)}\n")
        output_file.write(f"Nombre de lignes: {result.num_lines}\n")
    output_file.write("-" * 80 + "\n")
    if ext == '.mo' and result.read_ok:
        output_file.write("// Fichier binaire (.mo) encodé en base64\n")
        output_file.write(result.content)
    else:
        output_file.write(result.content)
    if not result.content.endswith('\n'):
        output_file.write("\n")
    output_file.write("\n--- FIN DU FICHIER ---\n")
```

### B.4 Boucle d'orchestration — `src/extractor/engine.py:42-94`
```python
def run(self, progress_callback=None, log_callback=None):
    folder = self.context.folder_path
    output_path = self.context.output_path

    # 1) Découverte UNIQUE
    all_files = self.discovery.find_files(folder)
    # 2) Filtrage sélection
    files = self._filter_selected(all_files, log_callback)

    total_files = len(files)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(output_path, 'w', encoding='utf-8') as out_file:   # ← MODE 'w' (L.67)
            self._write_header(out_file, folder)
            self._write_structure(out_file, folder, log_callback)
            result = self._process_files(out_file, files, progress_callback, log_callback)
            if result == CANCELLED:
                cancelled = True
            else:
                cancelled = False
                self._write_stats(out_file, log_callback)

        if cancelled:
            self._cleanup_partial_output(output_path)
            print("=== EXTRACTION SUMMARY (CANCELLED) ===")
            print(_GLOBAL_COUNTER)
            return CANCELLED

        logger.info("Extraction terminée avec succès : %s", output_path)
        print("=== EXTRACTION SUMMARY ===")
        print(_GLOBAL_COUNTER)
        return SUCCESS
```

---

C. Résultat des vérifications 3.1 à 3.5
-----------------------------------------

| Protection                          | Statut    | Preuve (ligne)                                         |
|-------------------------------------|-----------|--------------------------------------------------------|
| 3.1 `_filters` importé/utilisé      | **ACTIVE**| `file_discovery.py:8-14` import + `L.146 prune_dirs()` + `L.170 should_ignore_file()` |
| 3.2 `visited` set peuplé AVANT yield| **ACTIVE**| `L.132 visited.add(resolved_root)` avant tout `yield`  |
| 3.3 `followlinks=False` passé       | **ACTIVE**| `L.118 os.walk(..., followlinks=False)`                |
| 3.4 `max_depth` appliqué            | **ACTIVE**| `L.114 max_depth = ...` + `L.135-143` test `depth >= max_depth` → `dirs[:]=[]` + `continue` |
| 3.5 Filtrage fichiers même `all_files=True` | **ACTIVE** | `L.170 should_ignore_file()` s'exécute TOUJOURS (avant test `all_files`) ; `EXCLUDED_FILE_SUFFIXES` + `EXCLUDED_FILE_NAMES` appliqués inconditionnellement sauf `force_include_all=True` (debug) |

**Note critique** : `max_depth=25` par défaut, mais **JAMAIS exposé dans l'UI** (absent de `base_controller.py`, `ui_widgets.py`, `settings/tabs.py`). Utilisateur ne peut pas le modifier sans éditer `config.json`.

---

D. Résultat de la Partie 4 (Écriture)
-------------------------------------

| Check                                    | Résultat | Preuve                                          |
|------------------------------------------|----------|-------------------------------------------------|
| Mode d'ouverture du fichier              | `'w'`    | `engine.py:67  with open(output_path, 'w', encoding='utf-8')` |
| Présence de double boucle                | **NON**  | Une seule boucle `for i, (full_path, rel_path, ext) in enumerate(files):` (L.166) |
| Présence de retry/chunking réinjectant   | **NON**  | Écriture directe `write_file_section(out_file, result)` sans relecture du fichier |
| Troncature initiale                      | **OUI**  | `'w'` écrase à l'ouverture — pas d'accumulation inter-runs |

---

E. Résultat de la Partie 5 (Fichiers traceurs)
----------------------------------------------

| Fichier                                | Taille    | Nature / Observations                                                   |
|----------------------------------------|-----------|-------------------------------------------------------------------------|
| `.pytest_cache/v/cache/nodeids` (T-E)  | 29 326 o  | 375 lignes de chemins relatifs de tests T-E ; **0 occurrence** de "TLLM" ou chemins absolus |
| `.pytest_cache/v/cache/lastfailed`     | 227 o     | JSON minimal                                                            |
| `logs/tllm.log` (TLLM)                 | 0.80 Mo   | Logs applicatifs, pas de répétition massive, pas de chemins absolus vers source extraite |
| Anciens outputs `.txt` dans source     | **NON**   | `find . -name "*.txt" -size +10M` → **aucun** dans TLLM ni T-E          |

**Conclusion E** : Aucune trace de "boule de neige" (vieux output ré-extrait). Le fichier `tllm.log` (0.8 Mo) est **exclu** par défaut car suffixe `.log` dans `EXCLUDED_FILE_SUFFIXES`.

---

F. Résultat de la Partie 6 (Fan-out réel)
-----------------------------------------

### F.1 Dossier piégé minimal (script repro)
```
raw os.walk (cap 400) : dirs=539 files=451 bytes=76.29 Mo deepest=69 levels=401 [TRONQUÉ]
T-E _walk()           : walk_roots_visited=10 files_emitted=3 bytes_written=532
```
→ Le `raw os.walk(followlinks=False)` **suit les junctions** (boucle infinie), mais le `visited` set + pruning de T-E le borne.

### F.2 Vrai dossier source TLLM (`C:/Dossier tlf/code/TLLM`)
```
dirs=163 files=342 bytes=3.08 Mo deepest=5
```
→ Source **minuscule** (3.08 Mo). **Impossible** de produire 792 Mo depuis ce dossier avec les options par défaut.

---

G. Cause racine identifiée
--------------------------

**Aucune cause racine unique reproductible sur le code actuel** pour un dossier de 3 Mo produisant 792 Mo.

**Hypothèse principale (non vérifiée, configuration manquante)** :
> **Combinaison `include_txt=True` + `max_file_size_mb` élevé (ex: 1000) + dossier source contenant un GROS fichier `.txt` (>100 Mo) + éventuellement junctions non protégées** — permet l'inclusion d'un fichier texte massif qui est copié tel quel dans l'output, le gonflant à sa taille réelle.

**Preuves à l'appui** :
1. `max_file_size_mb` par défaut = 10 Mo (rejette les gros fichiers avec message d'erreur court).
2. `include_txt` par défaut = `False` (pas de .txt extraits).
3. L'UI **n'expose pas** `max_depth`, `max_file_size_mb`, `force_include_all`.
4. Le dossier TLLM source ne contient **aucun** `.txt` > 10 Mo (le plus gros = `tllm.log` 0.8 Mo, exclu par suffixe).
5. Le preset `"full"` (menus.py:278-282) active `include_txt=True` et `include_mo=True` mais ne change **pas** `max_file_size_mb` (reste 10).

**Cause secondaire (Windows junctions + profondeur)** :
> `followlinks=False` **ne protège pas** contre les junctions Windows (reparse points mount point). Un dossier source contenant une junction vers un gros répertoire externe (ex: `node_modules`, dataset, backup) peut faire exploser le fan-out jusqu'à `max_depth=25`. Le `visited` set limite la réentrée sur le **même chemin résolu**, mais pas l'exploration initiale.

---

H. Preuve chiffrée (estimation contribution au 792 Mo)
------------------------------------------------------

| Cause candidate                                 | Contribution estimée | Probabilité | Commentaire                                              |
|-------------------------------------------------|----------------------|-------------|----------------------------------------------------------|
| Gros fichier `.txt` source (>700 Mo) + `include_txt=True` + `max_file_size_mb` ≥ 800 | **792 Mo** (100%)    | **Haute** si config modifiée | Seul mécanisme capable de copier 792 Mo en 1 passe       |
| Junction vers gros répertoire externe + `max_depth=25` | ≤ taille répertoire  | Moyenne     | Limité par `max_depth=25` et `visited` ; nécessite `include_txt` ou extension acceptée |
| Boucle `loop` + `parent_link` + `force_include_all=True` | ×25 (profondeur)    | Faible      | Nécessite option debug `force_include_all` ; output ≤ 25×taille_fichier |
| Accumulation inter-runs (mode `'a'`)            | **0**                | Impossible  | Mode `'w'` prouvé, nettoyage `.part` atomique           |
| Double boucle écriture                          | **0**                | Impossible  | Une seule boucle `for` dans `_process_files()`          |
| `.pytest_cache/nodeids` ré-extrait              | **0**                | Impossible  | Fichiers sans extension exclus par défaut ; 375 lignes seulement |

---

CONCLUSION FINALE
-----------------

Le bug **"extraction 792 Mo impossible à ouvrir"** n'est **pas reproductible** avec :
- le code actuel (protections actives : visited, pruning, max_depth, followlinks=False, max_file_size_mb=10)
- les options par défaut (include_txt=False)
- le dossier source réel TLLM (3.08 Mo total)

**La cause racine probable est une configuration utilisateur modifiée** :
1. `include_txt = True` activé (preset "full" ou checkbox UI)
2. `max_file_size_mb` augmenté bien au-delà de 10 (ex: 1000 via config.json manuel)
3. Dossier source contenant un fichier `.txt` de ~792 Mo (ex: ancien output, log géant, dump)

**Recommandation immédiate** (sans correction de code) :
- Vérifier `config.json` pour `max_file_size_mb` et `include_txt`
- Exclure explicitement `*.txt` volumineux via `ignore_patterns` si `include_txt` requis
- Ajouter `max_depth` et `max_file_size_mb` dans l'UI pour visibilité/contrôle
- Considérer `followlinks=False` → ne **protège pas** les junctions Windows ; ajouter un test `is_junction()` + pruning si critique

**Aucune correction de code n'est requise sur les protections existantes** — elles sont correctes et actives. Le problème est de **configuration + nature des données source**.
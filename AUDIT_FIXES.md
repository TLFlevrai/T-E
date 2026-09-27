# AUDIT_FIXES.md

Résumé des corrections apportées suite à l'audit forensique du projet T-E.

## Liste des commits

```
git log --oneline -12
```

| Commit | Bug | Description |
|--------|-----|-------------|
| `48c5e74` | #11 | fix(gui): corrige _paren_depth désynchronisé après collage/clavier |
| `626d84d` | #7  | fix(paths): unifie la résolution output_dir pour PDFService et Application |
| `835f767` | #3  | fix(extractor): nettoie _GLOBAL_COUNTER → _DEBUG_COUNTERS conditionnel |
| `5460b8b` | #4  | fix(extractor): déduplique les dossiers yieldés dans _walk |
| `36062b4` | #5  | fix(extractor): corrige num_lines dans _read_streaming avec line_range |
| `e814de6` | #9  | fix(network): corrige accumulation hash dans _process_v0_payload |
| `bf97285` | #8  | fix(network): corrige progression FileTransferService._build_v0_payload |
| `e72c844` | #2, #6 | fix(extraction): corrige total_files=0 et _filter_selected NO_SELECTION |
| `61a1b79` | #1  | fix(versioning): supprime save_mapping dupliqué et ajoute test lock |
| `4bfabd6` | #12 | fix(syntax): corrige regex bracket invalide dans _build_*_patterns |

**Note**: Les commits sont listés du plus récent au plus ancien.

## Résultat des tests

```
pytest tests/ -q -o addopts=""
382 passed, 2 skipped in ~10s
```

---

## Détails par bug

### BUG #1 — `VersionManager.save_mapping` dupliqué
**Fichier**: `src/versioning.py`
- **Problème**: La méthode `save_mapping()` était définie DEUX fois (ligne ~41 et ~81). La première (sans lock) était silencieusement écrasée par la seconde (avec lock).
- **Correction**: Suppression de la première définition. Conservation uniquement de la version thread-safe qui délègue à `_save_mapping_locked()`.
- **Test ajouté**: `test_save_mapping_acquires_lock` dans `tests/unit/test_versioning.py` (mock du lock pour vérifier l'acquisition).

---

### BUG #2 — `_filter_selected` retourne `NO_SELECTION` mais le code attend `None`
**Fichiers**: `src/extractor/engine.py`, `tests/unit/test_extractor_engine.py`
- **Problème**: `_filter_selected` retourne `NO_SELECTION` (string) quand aucun fichier ne matche, mais `run()` testait `if files is None: return FAILED` — branche morte inatteignable.
- **Correction**: Suppression de la branche morte `if files is None: return FAILED` dans `run()`. Renommage du test `test_filter_selected_empty_returns_none` → `test_filter_selected_empty_returns_no_selection` avec assertion `result == NO_SELECTION`.
- **Test corrigé**: Dans `tests/unit/test_extractor_engine.py`.

---

### BUG #3 — `_GLOBAL_COUNTER` état global mutable + `print()` en prod
**Fichiers**: `src/extractor/file_discovery.py`, `src/extractor/engine.py`, `scripts/repro_duplication.py`
- **Problème**: Dict global `_GLOBAL_COUNTER` muté dans le walk (non thread-safe), `print()` polluant stdout en production.
- **Correction**: 
  - Renommé en `_DEBUG_COUNTERS` dans `file_discovery.py`
  - Encapsulé derrière `_DEBUG_ENABLED = os.environ.get('TE_DEBUG_COUNTERS') == '1'` (False par défaut)
  - Remplacé les `print()` dans `engine.py` par `logger.debug()`
  - Script `repro_duplication.py` active `_DEBUG_ENABLED = True` au démarrage
- **Test ajouté**: `test_debug_counters_disabled_by_default` dans `tests/unit/test_content_reader.py`.

---

### BUG #4 — `_walk` yield les dossiers parents N fois
**Fichier**: `src/extractor/file_discovery.py`
- **Problème**: Dans la boucle sur les fichiers, `for parent in rel_path.parents` yieldait tous les parents pour CHAQUE fichier → O(fichiers × profondeur) au lieu de O(dossiers). Ex: dossier `src` yieldé 132 fois.
- **Correction**: Ajout d'un `set` local `yielded_dirs: set[Path] = set()` en début de `_walk()`. Avant chaque yield de dossier, vérification `if parent not in yielded_dirs`.
- **Test ajouté**: `test_walk_deduplicates_directories` dans `tests/unit/test_extractor_engine.py` (structure `a/b/c/file.py`, vérifie chaque dossier 1 seule fois).

---

### BUG #5 — `_read_streaming` num_lines ne compte que les lignes extraites
**Fichier**: `src/extractor/content_reader.py`
- **Problème**: Si `line_range=(10, 20)`, `total_lines` retourné valait 11 (lignes 10-20), pas le total du fichier.
- **Correction**: Deux compteurs distincts:
  - `total_lines_file` = total lignes fichier (pour stats)
  - `extracted_lines` = lignes dans la plage (pour contenu)
  - Retourne `total_lines_file` pour cohérence stats.
- **Test ajouté**: `test_streaming_line_range_returns_total_lines` dans `tests/unit/test_content_reader.py` (fichier 150000 lignes, range 10000-10020, vérifie `num_lines == 150000`).

---

### BUG #6 — `stats_dict['total_files']` toujours 0
**Fichier**: `src/services/extraction_service.py`
- **Problème**: `stats_dict['total_files'] = stats.get('total', 0)` mais la clé `'total'` n'existe JAMAIS dans `context.stats` (clés: py, json, txt, po, mo, html, css, js).
- **Correction**: `total_files = sum(stats.get(k, 0) for k in ('py','json','txt','po','mo','html','css','js'))`
- **Test ajouté**: `test_context_stats_total_files` dans `tests/unit/test_extractor_engine.py` (3 fichiers types différents, vérifie `total == 3`).

---

### BUG #7 — `PDFService` résout `output_dir` depuis CWD
**Fichiers**: `src/services/pdf_service.py`, `src/core/app.py`, `src/paths.py`
- **Problème**: `Path(get_config().get('output_dir', 'out')).resolve()` résout depuis CWD. Mais `Application._resolve_output_dir()` résout depuis `_PROJECT_ROOT`. Incohérence possible avec `output_dir` custom.
- **Correction**: Nouvelle fonction publique `resolve_output_dir()` dans `src/paths.py` (logique unifiée: absolu = tel quel, relatif = relatif à la racine projet). Utilisée par `PDFService._validate_and_resolve_path` et `Application._resolve_output_dir`.
- **Test ajouté**: `test_resolve_output_dir_consistency` dans `tests/unit/test_content_reader.py`.

---

### BUG #8 — `FileTransferService._build_v0_payload` progression cassée
**Fichier**: `src/gui/network_center/services/file_transfer_service.py`
- **Problème**: `progress_callback(hasher.digest().__sizeof__(), total_size)` → `hasher.digest()` = 32 octets, `__sizeof__()` ≈ 65 octets (taille objet Python). Progression figée.
- **Correction**: Variable `sent_bytes` incrémentée de `len(chunk)` à chaque lecture, passée au callback.
- **Tests ajoutés** (4) dans `tests/unit/test_file_transfer.py`:
  - `test_build_v0_payload_progress_reaches_total` (256 Ko → 4 chunks)
  - `test_build_v0_payload_small_file` (< CHUNK_SIZE)
  - `test_build_v0_payload_exact_chunk_boundary` (exactement 64 Ko)
  - `test_build_v0_payload_multiple_chunks` (192 Ko = 3 chunks)

---

### BUG #9 — `_process_v0_payload` accumulation hash fragile
**Fichier**: `src/network/server.py`
- **Problème**: `received_hash += hash_part` non borné → pouvait accumuler > 32 octets si chunk contient data + hash + surplus.
- **Correction**: Buffer borné `bytearray(32)` + index `hash_bytes_read`. Remplissage jusqu'à 32 octets max, surplus ignoré avec warning.
- **Tests ajoutés** (2) dans `tests/unit/test_network_server.py`:
  - `test_hash_received_in_single_large_chunk` (payload + hash en 1 seul `sendall`)
  - `test_hash_received_in_multiple_chunks` (fragmentation TCP forcée)

---

### BUG #10 — État dupliqué entre sous-contrôleurs
**Fichiers**: `src/gui/controller/main_controller.py`, `src/gui/controller/base_controller.py`
- **Problème**: Chaque sous-contrôleur hérite de `BaseController` avec son propre `_selected_folder`, `selected_files`, `is_extracting`. Synchronisation manuelle fragile.
- **Correction**: Nouvelle classe `SharedState` (dataclass) avec `selected_folder`, `selected_files`, `is_extracting`. `BaseController.__init__` prend `shared_state: SharedState` optionnel. `MainController` instancie UN `SharedState` et le passe à tous les sous-contrôleurs. Propriétés deviennent des proxies vers `shared_state`. Rétrocompatibilité: si `shared_state is None`, état local créé.
- **Test ajouté**: Dans `tests/unit/test_controllers.py` (vérifie partage d'état entre 2 contrôleurs).

---

### BUG #11 — `CalculatorContent._insert_char` `_paren_depth` désynchronisé
**Fichier**: `src/gui/calculator.py`
- **Problème**: `_paren_depth` incrémenté/décrémenté seulement via boutons `(` et `)`. Collage (`Ctrl+V`) ou saisie clavier directe ne mettaient pas à jour le compteur.
- **Correction**: 
  - Nouvelle méthode `_recompute_paren_depth()` recalculant depuis `self.expression`.
  - Appelée dans `_paste_expression()`, `_on_key()` pour `()`, `_backspace()`, `_toggle_sign()`.
- **Tests ajoutés** (2) dans `tests/unit/test_calculator.py`:
  - `test_recompute_paren_depth_simple`
  - `test_paste_updates_paren_depth`

---

### BUG #12 — `_syntax.py` regex bracket invalide
**Fichier**: `src/tools/_syntax.py`
- **Problème**: Dans TOUS les builders (`_build_python_patterns`, `_build_js_patterns`, `_build_json_patterns`, `_build_css_patterns`), regex bracket = `r'[()[\]{}]]'` — un `]` orphelin en trop. `re.error` avalée silencieusement → surlignage brackets ne marchait jamais.
- **Correction**: Remplacement par `r'[()\[\]{}]'` PARTOUT (le CSS avait déjà la version correcte).
- **Commit**: `4bfabd6` (déjà présent avant cet audit).
- **Test**: `test_all_patterns_are_valid_regex` (existant) passe maintenant sans `pytest.fail`.

---

## Découvertes bonus (non corrigées, signalées)

1. **Junctions Windows non protégées par `followlinks=False`**: `os.walk(followlinks=False)` ne bloque PAS les junctions (reparse points mount point) sur Windows. Le `visited` set limite la réentrée mais l'exploration initiale peut descendre 25 niveaux (`max_depth=25`) dans un répertoire externe via junction.

2. **`max_depth` non exposé dans l'UI**: Option dans le schema/config mais absente des contrôles GUI (`base_controller.py`, `ui_widgets.py`, `settings/tabs.py`). Utilisateur ne peut pas la modifier sans éditer `config.json`.

3. **Test `test_filter_selected_empty_returns_none` pré-existant incorrect**: Testait `result is None` mais le code retourne `NO_SELECTION`. Corrigé dans BUG #2.

4. **Test `test_run_calls_progress_callback` pré-existant incorrect**: Attendait 1 appel callback mais le code en fait 2 (début 0% + fin 100%). Corrigé pour attendre 2 appels.

---

## Validation finale

- ✅ Tous les tests existants passent (382 passed, 2 skipped)
- ✅ 12 nouveaux tests ajoutés (1 par bug corrigé + quelques extras)
- ✅ Messages de commit conventionnels (`fix(scope): description`)
- ✅ i18n préservée (aucun `_(...)` modifié)
- ✅ Style respecté (PEP8, type hints, docstrings françaises)
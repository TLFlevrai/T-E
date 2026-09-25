# TE — Toolkit Multi-Outils

![Version](https://img.shields.io/badge/version-0.0.3-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-GPL--3.0-orange)

Application de bureau Python/Tkinter regroupant un ensemble d'outils pour l'extraction de code, la conversion de fichiers, le téléchargement vidéo, le transfert réseau et la personnalisation de l'interface.

---

## Aperçu

TE est une application tout-en-un conçue pour les développeurs. Elle offre une interface unifiée avec une barre latérale navigable, un workspace central et un système de thème personnalisable.

```
┌─────────────┬──────────────────────────────────┐
│  Sidebar    │  ☰  [Workspace]                  │
│             │                                   │
│  📁 Extraire│  Vue de l'outil actif             │
│  🔄 Convert │                                   │
│  🎬 Vidéo   │                                   │
│  🧮 Calc    │                                   │
│  🌐 Réseau  │                                   │
│  ▶️ YouTube │                                   │
│  🗂️ Versions│                                  │
│  🧰 Outils  │                                   │
│  ⚙️ Param   │                                   │
└─────────────┴──────────────────────────────────┘
```

---

## Outils

| Raccourci | Outil | Description |
|-----------|-------|-------------|
| `Ctrl+1` | **Extraction** | Extraire le code et la structure d'un projet dans un fichier `.txt` |
| `Ctrl+2` | **Builder** | Reconstituer un projet à partir d'un journal T-E |
| `Ctrl+3` | **Versions** | Gérer les versions d'export des projets |
| `Ctrl+4` | **Conversion** | Convertir des fichiers : TXT↔PDF, JSON→TXT, Images, CSV→JSON, Audio, Batch |
| `Ctrl+5` | **YouTube** | Télécharger des vidéos YouTube (MP4 ou MP3) |
| `Ctrl+6` | **Diff** | Comparer deux fichiers côte à côte |
| `Ctrl+7` | **Couleurs** | Sélecteur de couleurs avec palette et export |
| `Ctrl+8` | **Analyseur** | Statistiques de texte, fréquence, encodage, minification |
| `Ctrl+9` | **Bloc-notes** | Éditeur multi-onglets avec surlignage syntaxique |
| `Ctrl+0` | **Calculatrice** | Calculatrice standard, scientifique, pourcentage, bases, unités |
| `Ctrl+K` | **Palette** | Rechercher et lancer un outil ou une action |

---

## Fonctionnalités principales

### Extraction de code

Scanne un dossier projet et exporte le contenu dans un fichier texte unique, avec structure de dossiers, statistiques et métadonnées.

- Formats supportés : Python, JSON, TXT, PO/MO, HTML, CSS, JS
- Filtrage : `__pycache__`, `.git`, `__init__.py`
- Préréglages : Python uniquement, Assets Web, Complet, Minimal
- Export PDF intégré
- Sélection individuelle des fichiers
- Barre de latérale repliable via le bouton `☰`

### Conversion de fichiers (Alchimiste)

Six modes de conversion intégrés au workspace :

| Mode | Onglet | Description |
|------|--------|-------------|
| Documents | TXT→PDF, PDF→TXT | Génération PDF avec police Courier |
| Vidéo→MP3 | ffmpeg/pydub | Extraction audio de vidéos |
| Images | PNG↔JPG↔BMP↔WEBP | Conversion + redimensionnement |
| CSV→JSON | csv, json | Conversion avec délimiteur configurable |
| Audio | MP3↔WAV↔OGG | Conversion entre formats audio |
| Batch | Tous types | Conversion en lot de plusieurs fichiers |

### Téléchargement YouTube

Télécharge des vidéos YouTube en MP4 (vidéo) ou MP3 (audio) via `yt-dlp`.

- Qualités : 360p, 480p, 720p, 1080p, 2160p (4K)
- Choix du format avant lancement
- Barre de progression en temps réel
- Nécessite `ffmpeg` pour l'extraction audio

### Réseau / Transfert de fichiers

Système de transfert TCP sur le réseau local avec découverte automatique.

- **Serveur TCP** : réception de fichiers avec authentification HMAC-SHA256
- **Découverte UDP** : broadcast LAN pour trouver les pairs
- **Sécurité** : token d'auth, filtrage par extension, protection path traversal
- **Intégrité** : hash SHA-256 vérifié à la réception
- **Interface** : onglets Envoi, Reçus, Journal, Statut

> ⚠ **Usage LAN** : Par défaut, le serveur écoute uniquement sur `127.0.0.1` (localhost).
> Pour activer l'écoute sur le réseau local, configurez `network.server_host: "0.0.0.0"` dans `config.json`
> **et** définissez un `network.auth_token` unique (pas la valeur par défaut).
> Un avertissement s'affichera au démarrage : *le trafic n'est PAS chiffré, utilisez un VPN ou tunnel SSH
> sur réseaux non de confiance*.

### Gestion des versions

Suivi des versions d'export par projet (`projectNamev1.txt`).

- Scan, archivage, restauration, suppression de versions
- Explorateur de versions avec arborescence et aperçu
- Archivage automatique des anciennes versions

### Personnalisation

- **Thème** : système de design « Graphite & Cyan » avec palettes clair/sombre/personnalisée
- **Éditeur de thème** : modification live des couleurs
- **Langues** : français/anglais, changement à chaud sans redémarrage
- **Raccourcis** : personnalisables par commande
- **Réinitialisation** : bouton « Factory Reset » pour tout remettre par défaut

---

## Installation

### Prérequis

- Python >= 3.10
- pip (ou [uv](https://github.com/astral-sh/uv) recommandé pour reproductibilité)

### Dépendances

Avec pip :
```
pip install pydantic fpdf2 pillow resvg-py yt-dlp PyPDF2 pydub chardet
```

Ou installer toutes les dépendances (prod + dev) :
```
pip install -r requirements.txt
```

Avec uv (reproductible, lock file `uv.lock`) :
```
uv sync
```
Ou pour installer seulement les dépendances de production :
```
uv sync --no-dev
```

Optionnel (thème premium) :
```
pip install ttkbootstrap
# ou
uv add ttkbootstrap
```

### Lancement

```bash
python main.py
# ou avec uv
uv run python main.py
```

---

## Structure du projet

```
main.py                     Point d'entrée
config.json                 Configuration runtime
pyproject.toml              Métadonnées et outils
requirements.txt            Dépendances production
requirements-dev.txt        Dépendances développement

src/
  config/                   Schéma Pydantic et singleton config
    schema.py               AppConfig, NetworkConfig, ExtractionOptions, GuiConfig
    __init__.py             _Config (thread-safe), get_config()

  core/                     Couche domaine / architecture
    app.py                  Application (Composition Root)
    tool.py                 Dataclass Tool
    tool_registry.py        Registre des outils
    command_registry.py     Registre des commandes
    events.py               Bus d'événements sync
    shortcuts.py            Gestionnaire de raccourcis

  extractor/                Moteur d'extraction
    engine.py               Pipeline d'extraction
    file_discovery.py       Découverte de fichiers
    content_reader.py       Lecture du contenu
    export_writer.py        Écriture de l'export
    structure_generator.py  Génération de l'arborescence
    context.py              ExtractionContext
    report_builder.py       Génération de rapports
    statistics_collector.py Collecte de statistiques

  services/                 Couche use-case
    extraction_service.py   Orchestre extraction + versioning
    pdf_service.py          Export TXT → PDF
    version_service.py      Scan/archive/restore/delete versions

  network/                  Couche réseau
    server.py               Serveur TCP (réception, auth, streaming)
    discovery.py            Découverte UDP (broadcast LAN)

  gui/                      Vues et widgets
    theme.py                Système de design (tokens, palettes, styles)
    theme_editor.py         Éditeur de thème live
    calculator.py           Calculatrice (5 modes)
    video_converter.py      Convertisseur vidéo
    extraction_runner.py    Gestionnaire de thread d'extraction
    crash_report.py         Rapport de crash
    app_guard.py            Garde-fou applicatif
    premium.py              Fonctionnalités premium
    controller/             Contrôleurs MVC
    settings/               Onglets de paramètres
    selection/              Sélection de fichiers
    network_center/         Centre de transfert réseau
    version_explorer/       Explorateur de versions
    ui_builder/             Widgets, menus, tooltips

  tools/                    Outilses secondaires
    builder.py              Reconstitution de projet T-E
    converter.py            Alchimiste (6 conversions)
    youtube.py              TéléScope (YouTube)
    diff.py                 DualiS (comparaison)
    color_picker.py         Prisme (couleurs)
    text_analyzer.py        Analyseur de texte (5 onglets)
    notepad.py              Bloc-notes amélioré
    _syntax.py              Moteur de surlignage
    _text_stats.py          Statistiques de texte
    versions.py             Gestionnaire de versions
    network.py              Outils réseau
    tools_hub.py            Hub d'outils
    settings.py             Paramètres

  ui/                       Framework UI
    shell.py                Fenêtre principale (sidebar + workspace)
    sidebar.py              Barre latérale (recherche, catégories, scroll)
    workspace.py            Zone centrale (cache de vues, AutoScrollFrame)
    autoscroll.py           Défilement automatique
    command_palette.py      Palette de commandes (Ctrl+K)
    tooltips.py             Tooltips riches

locale/                     Traductions
  fr/LC_MESSAGES/           Français (défaut)
  en/LC_MESSAGES/           Anglais

tests/                      Tests
  unit/                     Tests unitaires (322+ tests)
  integration/              Tests d'intégration
  conftest.py               Configuration pytest

out/                        Dossier de sortie des exports
assets/                     Logo, icônes
```

---

## Configuration

Toutes les options sont dans `config.json` (auto-généré au premier lancement).

| Section | Options clés |
|---------|-------------|
| `language` | `"fr"` ou `"en"` |
| `output_dir` | Dossier de sortie (défaut : `"out"`) |
| `extraction.*` | Types de fichiers, sous-dossiers, statistiques |
| `network.*` | Hôte, port, token d'auth, extensions autorisées |
| `gui.window_width/height` | Taille de la fenêtre (défaut : 1100×750) |
| `gui.theme` | `"system"`, `"light"`, `"dark"`, `"custom"` |

---

## Commandes globales

| Raccourci | Action |
|-----------|--------|
| `Ctrl+K` | Ouvrir la palette de commandes |
| `Ctrl+Q` | Quitter TE |
| `Ctrl+E` | Lancer l'extraction |
| `Ctrl+O` | Parcourir un dossier |
| `Ctrl+L` | Effacer le journal |

---

## Licence

Licence publique générale GNU v3.0 — voir `pyproject.toml` pour les détails.

Ce logiciel est un logiciel libre distribué sous licence GPL-3.0.
Vous êtes libre de le modifier, le redistribuer et/ou le commercialiser
sous réserve du respect de la licence.

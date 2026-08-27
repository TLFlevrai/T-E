# TE — Toolkit Multi-Outils

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
| `Ctrl+2` | **Conversion** | Convertir des fichiers : TXT → PDF, PDF → TXT, JSON → TXT |
| `Ctrl+3` | **Vidéo** | Convertir des vidéos en fichiers MP3 |
| `Ctrl+4` | **Calculatrice** | Calculatrice intégrée |
| `Ctrl+5` | **Réseau** | Envoyer et recevoir des fichiers sur le réseau local |
| `Ctrl+6` | **Versions** | Gérer les versions d'export des projets |
| `Ctrl+7` | **Outils** | Hub d'utilitaires et personnalisation |
| `Ctrl+8` | **Paramètres** | Configurer la langue, le thème, les formats, la sortie |
| `Ctrl+9` | **YouTube** | Télécharger des vidéos YouTube (MP4 ou MP3) |
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

### Conversion de fichiers

Trois modes de conversion intégrés au workspace :

| Mode | Bibliothèque | Description |
|------|-------------|-------------|
| TXT → PDF | `fpdf2` | Génération PDF avec police Courier, sauts de page auto |
| PDF → TXT | `PyPDF2` | Extraction texte page par page |
| JSON → TXT | `json` | Formatage avec indentation configurable |

Options : encodage (UTF-8, Latin-1, CP1252, ASCII), indentation JSON.

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
- pip

### Dépendances

```
pip install pydantic fpdf2 pillow resvg-py yt-dlp PyPDF2
```

Optionnel (thème premium) :

```
pip install ttkbootstrap
```

### Lancement

```bash
python main.py
```

---

## Structure du projet

```
main.py                     Point d'entrée
config.json                 Configuration runtime
pyproject.toml              Métadonnées et outils

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
    calculator.py           Calculatrice
    video_converter.py      Convertisseur vidéo
    extraction_runner.py    Gestionnaire de thread d'extraction
    controller/             Contrôleurs MVC
    settings/               Onglets de paramètres
    selection/              Sélection de fichiers
    network_center/         Centre de transfert réseau
    version_explorer/       Explorateur de versions
    ui_builder/             Widgets, menus, tooltips

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

tests/                      Tests unitaires
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

Projet privé — tous droits réservés.

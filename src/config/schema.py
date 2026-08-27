# src/config/schema.py
from pydantic import BaseModel, Field


class NetworkConfig(BaseModel):
    """Configuration réseau pour le serveur et la découverte."""
    server_host: str = Field(default="127.0.0.1", description="Hôte d'écoute du serveur")
    server_port: int = Field(default=50000, ge=1024, le=65535, description="Port du serveur TCP")
    discovery_port: int = Field(default=50001, ge=1024, le=65535, description="Port UDP pour la découverte réseau")
    broadcast_msg: str = Field(default="PYEXTRACTOR_DISCOVER", description="Message de découverte broadcast")
    reply_msg: str = Field(default="PYEXTRACTOR_HERE", description="Message de réponse à la découverte")
    auth_enabled: bool = Field(default=True, description="Activer l'authentification par token")
    auth_token: str = Field(default="change-me-secure-random-token", description="Token secret partagé (min 32 chars recommandé)")
    allowed_extensions: list[str] = Field(default=[".txt"], description="Extensions de fichiers autorisées")


class ExtractionOptions(BaseModel):
    """Options de l'extraction."""
    include_json: bool = Field(default=True, description="Inclure les fichiers .json")
    include_subdirs: bool = Field(default=True, description="Parcourir les sous-dossiers")
    show_file_paths: bool = Field(default=True, description="Afficher les chemins complets des fichiers")
    include_structure: bool = Field(default=True, description="Inclure la structure du projet dans l'export")
    include_txt: bool = Field(default=False, description="Inclure les fichiers .txt")
    include_po: bool = Field(default=False, description="Inclure les fichiers .po (traductions)")
    include_mo: bool = Field(default=False, description="Inclure les fichiers .mo (compilés)")
    include_html: bool = Field(default=True, description="Inclure les fichiers .html et .htm")
    include_css: bool = Field(default=True, description="Inclure les fichiers .css")
    include_js: bool = Field(default=True, description="Inclure les fichiers .js")
    ignore_init: bool = Field(default=False, description="Ignorer les fichiers __init__.py")
    ignore_git: bool = Field(default=False, description="Ignorer le dossier .git et son contenu")
    ignore_pycache: bool = Field(default=True, description="Ignorer les dossiers __pycache__ et leur contenu")
    include_statistics: bool = Field(default=True, description="Inclure les statistiques dans l'export")
    include_file_metadata: bool = Field(default=False, description="Inclure les métadonnées par fichier (taille, lignes)")


class GuiConfig(BaseModel):
    """Configuration de l'interface graphique."""
    window_width: int = Field(default=1100, ge=400, le=1920, description="Largeur de la fenêtre")
    window_height: int = Field(default=750, ge=300, le=1080, description="Hauteur de la fenêtre")
    window_x: int = Field(default=-1, ge=-1, description="Position X de la fenêtre (-1 = centré)")
    window_y: int = Field(default=-1, ge=-1, description="Position Y de la fenêtre (-1 = centré)")
    version_window_width: int = Field(default=1000, ge=600, le=1920, description="Largeur fenêtre versions")
    version_window_height: int = Field(default=650, ge=400, le=1080, description="Hauteur fenêtre versions")
    version_window_x: int = Field(default=-1, ge=-1, description="Position X fenêtre versions (-1 = centré)")
    version_window_y: int = Field(default=-1, ge=-1, description="Position Y fenêtre versions (-1 = centré)")
    log_height: int = Field(default=12, ge=4, le=30, description="Hauteur du journal en lignes")
    log_autoscroll: bool = Field(default=True, description="Défiler automatiquement le journal")
    theme: str = Field(default="system", description="Thème : system, light, dark, custom")
    # Thème personnalisé (stocké comme JSON string ou dict)
    custom_theme: dict = Field(default_factory=dict, description="Couleurs du thème personnalisé")
    # Raccourcis clavier personnalisés : {command_id: accélérateur}
    shortcuts: dict[str, str] = Field(default_factory=dict, description="Raccourcis personnalisés par commande")
    # Dossier de téléchargement YouTube
    youtube_dir: str = Field(default="downloads", description="Dossier de destination des téléchargements YouTube")
    # Session
    last_folder: str = Field(default="", description="Dernier dossier sélectionné (restauré au démarrage)")


class AppConfig(BaseModel):
    """Configuration principale de l'application."""
    output_dir: str = Field(default="out", description="Dossier de sortie des exports")
    received_subdir: str = Field(default="received", description="Sous-dossier pour les fichiers reçus")
    archive_subdir: str = Field(default="old_out", description="Sous-dossier pour l'archive des anciennes versions")
    version_file: str = Field(default="extractor_version.txt", description="Nom du fichier de version")
    language: str = Field(default="fr", description="Langue de l'interface (fr ou en)")

    network: NetworkConfig = Field(default_factory=NetworkConfig, description="Configuration réseau")
    extraction: ExtractionOptions = Field(default_factory=ExtractionOptions, description="Options d'extraction")
    gui: GuiConfig = Field(default_factory=GuiConfig, description="Configuration de l'interface")

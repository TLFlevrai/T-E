# src/services/pdf_service.py
from __future__ import annotations
import os
import re
from pathlib import Path
from src.config import get_config
from src.logger import setup_logger

logger = setup_logger(__name__)


class PDFService:
    @staticmethod
    def convert_to_pdf(txt_path: Path, pdf_path: Path):
        """Convertit un fichier texte en PDF en préservant la mise en forme."""
        try:
            from fpdf import FPDF
        except ImportError:
            logger.error("La bibliothèque fpdf n'est pas installée. Installez-la avec 'pip install fpdf'.")
            raise ImportError("fpdf is required for PDF export")

        # VALIDATION SÉCURITÉ : Résoudre les chemins et vérifier qu'ils sont dans le dossier de sortie autorisé
        txt_path = PDFService._validate_and_resolve_path(txt_path, "fichier source")
        pdf_path = PDFService._validate_and_resolve_path(pdf_path, "fichier destination", must_be_in_output_dir=True)

        # Lire le contenu texte
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error("Erreur lors de la lecture du fichier texte : %s", e)
            raise

        # Nettoyer le contenu : remplacer les emojis et caractères non-latin1
        content = PDFService._sanitize_for_pdf(content)

        # Créer le PDF
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # Utiliser une police qui supporte plus de caractères
        try:
            from fpdf import FPDF
            if hasattr(pdf, 'add_font') and PDFService._is_fpdf2():
                pdf.set_font('Courier', size=8)
            else:
                pdf.set_font('Courier', size=8)
        except Exception:
            pdf.set_font('Courier', size=8)

        # Découper en lignes et ajouter au PDF avec gestion des lignes trop longues
        lines = content.splitlines()
        for line in lines:
            if len(line) > 1200:
                chunks = [line[i:i+1200] for i in range(0, len(line), 1200)]
                for chunk in chunks:
                    pdf.cell(0, 5, txt=chunk, ln=True)
            else:
                try:
                    pdf.cell(0, 5, txt=line, ln=True)
                except UnicodeEncodeError:
                    safe_line = PDFService._remove_non_latin1(line)
                    pdf.cell(0, 5, txt=safe_line, ln=True)

        # Écriture sécurisée : le chemin a déjà été validé
        pdf.output(str(pdf_path))
        logger.info("PDF généré : %s", pdf_path)
        return pdf_path

    @staticmethod
    def _validate_and_resolve_path(path: Path, description: str, must_be_in_output_dir: bool = False) -> Path:
        """
        Valide et résout un chemin de manière sécurisée.
        
        Args:
            path: Chemin à valider
            description: Description pour les messages d'erreur
            must_be_in_output_dir: Si True, le chemin doit être dans le dossier de sortie configuré
            
        Returns:
            Path résolu et validé
            
        Raises:
            ValueError: Si le chemin est invalide ou tente un path traversal
        """
        if path is None:
            raise ValueError(f"{description} : chemin None")

        try:
            # Résoudre le chemin absolu (résout les symlinks, .., .)
            resolved = path.resolve(strict=False)
        except Exception as e:
            raise ValueError(f"{description} : chemin invalide ({e})")

        # NOTE: Le check '..' in path.parts APRÈS resolve() est mort — resolve() élimine déjà '..' et '.'
        # La vraie protection contre le path traversal est relative_to(output_dir) ci-dessous
        # qui garantit que le chemin final est bien DANS le dossier autorisé.

        # Vérifier que le chemin est dans le dossier de sortie autorisé
        if must_be_in_output_dir:
            output_dir = Path(get_config().get('output_dir', 'out')).resolve()
            try:
                resolved.relative_to(output_dir)
            except ValueError:
                raise ValueError(
                    f"{description} : le fichier doit être dans le dossier de sortie "
                    f"({output_dir}), reçu : {resolved}"
                )

        # Vérifier l'extension pour le PDF
        if description == "fichier destination" and resolved.suffix.lower() != '.pdf':
            raise ValueError(f"{description} : l'extension doit être .pdf")

        # S'assurer que le dossier parent existe
        resolved.parent.mkdir(parents=True, exist_ok=True)

        return resolved

    @staticmethod
    def _sanitize_for_pdf(content: str) -> str:
        """Remplace les emojis et caractères problématiques par des équivalents texte."""
        emoji_map = {
            '📁': '[DIR] ', '📄': '[FILE] ', '🐍': '[PY] ', '🌐': '[PO] ',
            '📦': '[MO] ', '📝': '[TXT] ', '🌍': '[HTML] ', '🎨': '[CSS] ',
            '⚡': '[JS] ', '├──': '├── ', '└──': '└── ', '│': '|',
            '✅': '[OK] ', '❌': '[ERR] ', '⚠️': '[WARN] ', '🔍': '[SRCH] ',
            '✓': '[OK] ', '✗': '[ERR] ', '→': '->', '☐': '☐', '☑': '☑', '◐': '◐',
        }

        for emoji, replacement in emoji_map.items():
            content = content.replace(emoji, replacement)

        return PDFService._remove_non_latin1(content)

    @staticmethod
    def _remove_non_latin1(text: str) -> str:
        """Supprime les caractères qui ne sont pas encodables en latin-1."""
        def is_latin1_char(char):
            code = ord(char)
            if 0x20 <= code <= 0x7E:
                return True
            if 0xA0 <= code <= 0xFF:
                return True
            if code in (0x09, 0x0A, 0x0D):
                return True
            return False

        result = []
        for char in text:
            if is_latin1_char(char):
                result.append(char)
            else:
                replacement = PDFService._get_ascii_equivalent(char)
                if replacement:
                    result.append(replacement)
                else:
                    result.append('?')
        return ''.join(result)

    @staticmethod
    def _get_ascii_equivalent(char: str) -> str:
        """Retourne un équivalent ASCII pour un caractère Unicode si possible."""
        equivalents = {
            'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
            'à': 'a', 'â': 'a', 'ä': 'a',
            'î': 'i', 'ï': 'i',
            'ô': 'o', 'ö': 'o',
            'ù': 'u', 'û': 'u', 'ü': 'u',
            'ç': 'c', 'ñ': 'n',
            'œ': 'oe', 'æ': 'ae',
            '«': '"', '»': '"', '“': '"', '”': '"',
            '‘': "'", '’': "'",
            '–': '-', '—': '-',
            '…': '...',
        }
        return equivalents.get(char, None)

    @staticmethod
    def _is_fpdf2() -> bool:
        """Vérifie si fpdf2 est installé (version plus récente)."""
        try:
            from fpdf import FPDF
            return hasattr(FPDF, 'add_font')
        except ImportError:
            return False
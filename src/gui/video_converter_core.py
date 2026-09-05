# src/gui/video_converter_core.py
"""Logique centrale de conversion vidéo vers MP3 (sans UI)."""
from __future__ import annotations
from pathlib import Path
import subprocess
import threading
from typing import Callable, Optional
from src.logger import setup_logger

logger = setup_logger(__name__)


class VideoConversionOptions:
    """Options de conversion vidéo vers MP3."""
    
    def __init__(
        self,
        quality: str = '192k',
        sample_rate: str = '44100',
        channels: str = 'stereo',  # 'mono' ou 'stereo'
        volume: float = 1.0,
    ):
        self.quality = quality
        self.sample_rate = sample_rate
        self.channels = channels
        self.volume = volume


class VideoConverterCore:
    """Logique de conversion vidéo vers MP3 (sans dépendance UI)."""
    
    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._cancelled = False
    
    @staticmethod
    def check_ffmpeg() -> bool:
        """Vérifie si ffmpeg est disponible."""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    @staticmethod
    def get_supported_formats() -> list[str]:
        """Retourne la liste des extensions vidéo supportées."""
        return [
            '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv',
            '.webm', '.m4v', '.3gp', '.ogv', '.mpeg', '.mpg'
        ]
    
    @staticmethod
    def build_ffmpeg_command(
        input_path: Path,
        output_path: Path,
        options: VideoConversionOptions
    ) -> list[str]:
        """Construit la commande ffmpeg."""
        cmd = [
            'ffmpeg', '-y',
            '-i', str(input_path),
            '-vn',
            '-acodec', 'libmp3lame',
            '-b:a', options.quality,
            '-ar', options.sample_rate,
        ]
        
        if options.channels == 'mono':
            cmd.extend(['-ac', '1'])
        else:
            cmd.extend(['-ac', '2'])
        
        if options.volume != 1.0:
            cmd.extend(['-filter:a', f'volume={options.volume}'])
        
        cmd.append(str(output_path))
        return cmd
    
    def convert(
        self,
        input_path: Path,
        output_path: Path,
        options: VideoConversionOptions,
        on_progress: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[bool, Optional[str]], None]] = None,
    ) -> threading.Thread:
        """
        Lance la conversion dans un thread séparé.
        
        Args:
            input_path: Fichier vidéo source
            output_path: Fichier MP3 de sortie
            options: Options de conversion
            on_progress: Callback appelé avec message de progression
            on_complete: Callback appelé avec (success, error_message)
        
        Returns:
            Le thread de conversion
        """
        self._cancelled = False
        
        def run_conversion():
            try:
                cmd = self.build_ffmpeg_command(input_path, output_path, options)
                logger.info("Commande ffmpeg : %s", ' '.join(cmd))
                
                self._process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                
                # Surveiller la progression
                while True:
                    if self._cancelled and self._process:
                        self._process.terminate()
                        break
                    
                    output = self._process.stderr.readline()
                    if output == '' and self._process.poll() is not None:
                        break
                    if output and on_progress:
                        if 'time=' in output:
                            on_progress("Conversion en cours...")
                
                return_code = self._process.wait()
                
                if self._cancelled:
                    if on_complete:
                        on_complete(False, "Annulé par l'utilisateur")
                    return
                
                if return_code == 0:
                    if on_complete:
                        on_complete(True, None)
                else:
                    stderr_output = self._process.stderr.read()
                    logger.error("Erreur ffmpeg : %s", stderr_output)
                    if on_complete:
                        on_complete(False, stderr_output or "Erreur inconnue")
            
            except Exception as e:
                logger.error("Erreur lors de la conversion : %s", e)
                if on_complete:
                    on_complete(False, str(e))
            finally:
                self._process = None
        
        thread = threading.Thread(target=run_conversion, daemon=True)
        thread.start()
        return thread
    
    def cancel(self):
        """Annule la conversion en cours."""
        self._cancelled = True
        if self._process and self._process.poll() is None:
            try:
                self._process.terminate()
            except Exception:
                logger.warning("Échec de l'arrêt du processus ffmpeg", exc_info=True)
    
    def is_running(self) -> bool:
        """Vérifie si une conversion est en cours."""
        return self._process is not None and self._process.poll() is None
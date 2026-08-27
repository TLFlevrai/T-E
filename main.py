# main.py
"""Point d'entrée de TE (Toolkit desktop multi-outils).

La composition des dépendances et le cycle de vie sont gérés par
`src.core.app.Application`.
"""
from src.core.app import Application

__all__ = ['Application', 'main']


def main():
    """Point d'entrée principal."""
    Application().start()


if __name__ == "__main__":
    main()

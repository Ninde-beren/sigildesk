"""Emplacements des fichiers : ressources livrées et dossiers XDG de l'utilisateur."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Le paquet `sigildesk` (ce fichier est dans son sous-paquet `infra`).
PACKAGE_DIR = Path(__file__).resolve().parent.parent
# Racine du dépôt en développement, ou du dossier copié par install-user.sh.
APP_ROOT = PACKAGE_DIR.parent
QML_DIR = PACKAGE_DIR / "qml"
RESOURCES_DIR = PACKAGE_DIR / "resources"
ICONS_DIR = RESOURCES_DIR / "icons"
WALLPAPERS_DIR = RESOURCES_DIR / "wallpapers"
DEFAULT_CONFIG = APP_ROOT / "config" / "default.json"


def _xdg_dir(variable: str, fallback: str) -> Path:
    # La spécification XDG impose d'ignorer une valeur relative.
    value = os.environ.get(variable, "")
    if value and os.path.isabs(value):
        return Path(value)
    return Path.home() / fallback


@dataclass(frozen=True)
class UserPaths:
    """Dossiers propres à SigilDesk chez l'utilisateur. Rien n'est écrit ailleurs."""

    config_dir: Path
    data_dir: Path
    state_dir: Path
    cache_dir: Path

    @classmethod
    def from_environment(cls, root: Path | None = None) -> UserPaths:
        """`root` regroupe tout sous un dossier unique (tests, captures, démo)."""
        if root is not None:
            return cls(root / "config", root / "data", root / "state", root / "cache")
        return cls(
            _xdg_dir("XDG_CONFIG_HOME", ".config") / "sigildesk",
            _xdg_dir("XDG_DATA_HOME", ".local/share") / "sigildesk",
            _xdg_dir("XDG_STATE_HOME", ".local/state") / "sigildesk",
            _xdg_dir("XDG_CACHE_HOME", ".cache") / "sigildesk",
        )

    @property
    def config_file(self) -> Path:
        return self.config_dir / "config.json"

    @property
    def wallpapers_dir(self) -> Path:
        return self.data_dir / "wallpapers"

    @property
    def icons_dir(self) -> Path:
        """Icônes de remplacement déposées par l'utilisateur (`<nom>.svg` ou `.png`)."""
        return self.data_dir / "icons"

    @property
    def weather_cache(self) -> Path:
        return self.cache_dir / "meteo.json"

    @property
    def log_file(self) -> Path:
        return self.state_dir / "sigildesk.log"


def user_config_root() -> Path:
    return _xdg_dir("XDG_CONFIG_HOME", ".config")

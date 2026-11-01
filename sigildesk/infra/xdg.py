"""Standards XDG du bureau : dossiers de l'utilisateur et associations de fichiers.

- Dossiers : `~/.config/user-dirs.dirs` (format imposé par xdg-user-dirs) donne
  l'emplacement de Documents, Images, Vidéos… en français ou en anglais. Un
  dossier absent n'est jamais créé : on se rabat sur le dossier personnel et
  l'interface le signale.
- Associations MIME : lecture seule, par `xdg-mime query default`. SigilDesk ne
  réimplémente ni lecteur vidéo, ni rendu PDF, ni galerie ; un double-clic dans
  l'explorateur ouvre l'application associée. Ce module vérifie que ces
  associations pointent vers des outils légers et propose la commande à lancer
  sinon. Il ne modifie jamais rien.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from sigildesk.infra.processes import run_capture

# --- Dossiers de l'utilisateur -------------------------------------------------------

# clé de `catalog.FOLDER_KEYS` → (variable XDG, noms de dossier à essayer)
_XDG_KEYS = {
    "desktop": ("XDG_DESKTOP_DIR", ("Bureau", "Desktop")),
    "documents": ("XDG_DOCUMENTS_DIR", ("Documents",)),
    "downloads": ("XDG_DOWNLOAD_DIR", ("Téléchargements", "Downloads")),
    "pictures": ("XDG_PICTURES_DIR", ("Images", "Pictures")),
    "videos": ("XDG_VIDEOS_DIR", ("Vidéos", "Videos")),
    "music": ("XDG_MUSIC_DIR", ("Musique", "Music")),
}
_USER_DIR_LINE = re.compile(r'^\s*(XDG_[A-Z]+_DIR)\s*=\s*"(.*)"\s*$')


def parse_user_dirs(text: str, home: Path) -> dict[str, Path]:
    """Lit le contenu de `user-dirs.dirs` : `XDG_PICTURES_DIR="$HOME/Images"`."""
    dirs: dict[str, Path] = {}
    for line in text.splitlines():
        match = _USER_DIR_LINE.match(line)
        if not match:
            continue
        name, value = match.groups()
        if value.startswith("$HOME"):
            dirs[name] = home / value[len("$HOME"):].lstrip("/")
        elif value.startswith("/"):
            dirs[name] = Path(value)
    return dirs


def resolve_folder(key: str, home: Path, user_dirs_file: Path) -> tuple[Path, bool]:
    """Chemin du dossier `key` et indicateur « trouvé » (sinon : dossier personnel)."""
    if key == "home":
        return home, True
    variable, fallbacks = _XDG_KEYS[key]
    try:
        configured = parse_user_dirs(user_dirs_file.read_text(encoding="utf-8"), home).get(variable)
    except OSError:
        configured = None
    candidates = ([configured] if configured else []) + [home / name for name in fallbacks]
    for candidate in candidates:
        # xdg-user-dirs fait pointer un dossier désactivé sur $HOME : ce n'est pas un dossier dédié.
        if candidate != home and candidate.is_dir():
            return candidate, True
    return home, False


# --- Associations de fichiers -------------------------------------------------------

Runner = Callable[[list[str]], str]

# (type MIME, libellé, identifiants .desktop recommandés, par ordre de préférence)
CHECKS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("inode/directory", "Dossiers", ("pcmanfm-qt",)),
    ("image/jpeg", "Photos JPEG", ("lximage-qt",)),
    ("image/png", "Images PNG", ("lximage-qt",)),
    ("image/webp", "Images WEBP", ("lximage-qt",)),
    ("video/mp4", "Vidéos MP4", ("vlc", "org.videolan.vlc", "mpv", "io.mpv.mpv")),
    ("application/pdf", "Documents PDF", ("qpdfview",)),
)


@dataclass(frozen=True)
class AssociationReport:
    mime: str
    label: str
    current: str  # identifiant .desktop, ou "" si aucune association
    recommended: tuple[str, ...]
    status: str  # "ok", "autre" ou "aucune"

    @property
    def fix_command(self) -> str:
        """Commande à proposer à la personne qui maintient l'ordinateur (jamais exécutée par SigilDesk)."""
        return f"xdg-mime default {self.recommended[0]}.desktop {self.mime}"


def _subprocess_runner(argv: list[str]) -> str:
    return run_capture(argv, timeout=5) or ""


def desktop_base(desktop_id: str) -> str:
    return desktop_id[:-len(".desktop")] if desktop_id.endswith(".desktop") else desktop_id


def classify(current: str, recommended: tuple[str, ...]) -> str:
    if not current:
        return "aucune"
    base = desktop_base(current).lower()
    # qpdfview-qt6, vlc ou org.videolan.vlc comptent comme l'outil recommandé.
    if any(base == r.lower() or base.startswith(r.lower() + "-") for r in recommended):
        return "ok"
    return "autre"


def check_associations(xdg_mime: str | None, runner: Runner = _subprocess_runner) -> list[AssociationReport]:
    """Un rapport par type de `CHECKS` ; sans `xdg-mime`, tout est « aucune »."""
    reports = []
    for mime, label, recommended in CHECKS:
        output = runner([xdg_mime, "query", "default", mime]) if xdg_mime else ""
        current = output.strip().splitlines()[0].strip() if output.strip() else ""
        reports.append(AssociationReport(mime, label, current, recommended, classify(current, recommended)))
    return reports

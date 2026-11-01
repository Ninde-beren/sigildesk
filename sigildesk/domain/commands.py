"""Les commandes que SigilDesk peut lancer, décidées dans le code, jamais par la configuration.

La configuration ne fournit que des choix (navigateur préféré, dossier) et des
adresses validées par `urls.normalize_web_url`. `CommandBuilder` traduit ces
choix en une `Command` (programme + arguments séparés), sans rien exécuter :
c'est `infra.launcher` qui la passe à `QProcess.startDetached`. Aucun shell
n'intervient, et une adresse commence toujours par http(s)://, elle ne peut
donc pas être prise pour une option.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from sigildesk.domain.urls import UrlError, normalize_web_url

# Résout un nom de programme en chemin absolu, ou None s'il est absent.
Which = Callable[[str], "str | None"]

BROWSER_PROGRAMS: dict[str, tuple[str, ...]] = {
    "chromium": ("chromium", "chromium-browser"),
    "firefox": ("firefox",),
}
FILE_MANAGERS = ("pcmanfm-qt",)
OPENER = "xdg-open"

# Ordre d'essai selon le réglage « navigateur » ; « systeme » = xdg-open.
_BROWSER_ORDER: dict[str, tuple[str, ...]] = {
    "auto": ("chromium", "systeme"),
    "chromium": ("chromium", "systeme"),
    "firefox": ("firefox", "systeme"),
    "systeme": ("systeme",),
}

# Outils dont dépend l'expérience complète ; affichés dans Paramètres › Applications.
KNOWN_TOOLS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("chromium", "Navigateur Chromium", ("chromium", "chromium-browser")),
    ("firefox", "Navigateur Firefox", ("firefox",)),
    ("pcmanfm-qt", "Explorateur PCManFM-Qt", ("pcmanfm-qt",)),
    ("lximage-qt", "Visionneuse LXImage-Qt", ("lximage-qt",)),
    ("vlc", "Lecteur vidéo VLC", ("vlc",)),
    ("mpv", "Lecteur vidéo mpv", ("mpv",)),
    ("qpdfview", "Lecteur PDF qpdfview", ("qpdfview",)),
    ("xdg-open", "Ouverture standard (xdg-open)", ("xdg-open",)),
    ("lxqt-leave", "Extinction LXQt (lxqt-leave)", ("lxqt-leave",)),
    ("wmctrl", "Retour aux fenêtres ouvertes (wmctrl)", ("wmctrl",)),
)


class LaunchError(Exception):
    """Lancement impossible ; le message s'adresse à l'utilisateur."""


@dataclass(frozen=True)
class Command:
    program: str  # chemin absolu
    args: tuple[str, ...]

    def argv(self) -> list[str]:
        return [self.program, *self.args]


def first_available(which: Which, names: tuple[str, ...]) -> str | None:
    """Chemin du premier programme présent parmi `names`."""
    for name in names:
        path = which(name)
        if path:
            return path
    return None


class CommandBuilder:
    """Construit les commandes ; pur, sans effet de bord, donc testable avec un faux `which`."""

    def __init__(self, which: Which):
        self._which = which

    def browser_command(self, url: str, preference: str = "auto", app_window: bool = False) -> Command:
        """Commande du navigateur pour `url`.

        `app_window` : avec Chromium, fenêtre d'application sans barre d'adresse
        (`--app=`), maximisée ; les autres navigateurs ouvrent une fenêtre normale.
        """
        try:
            safe = normalize_web_url(url)
        except UrlError as exc:
            raise LaunchError(f"Adresse refusée : {exc}") from exc

        for choice in _BROWSER_ORDER.get(preference, _BROWSER_ORDER["auto"]):
            if choice == "systeme":
                opener = self._which(OPENER)
                if opener:
                    return Command(opener, (safe,))
                continue
            program = first_available(self._which, BROWSER_PROGRAMS[choice])
            if program:
                if app_window and choice == "chromium":
                    return Command(program, (f"--app={safe}", "--start-maximized"))
                return Command(program, (safe,))
        raise LaunchError("Aucun navigateur n'a été trouvé sur cet ordinateur.")

    def folder_command(self, folder: Path) -> Command:
        """Ouvre un dossier existant dans l'explorateur, sinon par xdg-open."""
        if not folder.is_absolute() or not folder.is_dir():
            raise LaunchError("Ce dossier est introuvable.")
        program = first_available(self._which, FILE_MANAGERS)
        if program:
            return Command(program, (str(folder),))
        opener = self._which(OPENER)
        if opener:
            return Command(opener, (str(folder),))
        raise LaunchError("Aucun explorateur de fichiers n'a été trouvé.")

    def available_tools(self) -> list[dict]:
        """`KNOWN_TOOLS` avec le chemin trouvé (ou « ») : pour le diagnostic et les Paramètres."""
        return [
            {"id": tool_id, "label": label, "path": first_available(self._which, names) or ""}
            for tool_id, label, names in KNOWN_TOOLS
        ]

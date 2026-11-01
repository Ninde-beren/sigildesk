"""Fenêtres ouvertes : les reconnaître pour les montrer et y revenir.

SigilDesk en plein écran cache la barre des tâches de LXQt. Sans aide, une
fenêtre restée ouverte derrière l'accueil serait perdue pour une personne
novice, et chaque clic sur une tuile en ouvrirait une nouvelle. L'accueil liste
donc les fenêtres dans sa propre barre, et une tuile ramène sa fenêtre au lieu
d'en ouvrir une autre.

Ce module lit la sortie de `wmctrl -lxp` (standard EWMH, session X11 de Lubuntu
sous Openbox) et décide du nom et de l'icône à montrer. Relevé dans Lubuntu
26.04 (WM_CLASS « instance.classe ») :

    www.youtube.com.Chromium   fenêtre d'application Chromium (--app=), instance = hôte
    chromium.Chromium          fenêtre de navigateur ordinaire
    pcmanfm-qt.pcmanfm-qt      dossier, avec son nom en titre (bureau : -1, ignoré)

L'appel à wmctrl est dans `infra.window_manager`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

# Instances des navigateurs en fenêtre ordinaire (toutes montrées comme « Internet »).
BROWSER_INSTANCES = frozenset({"chromium", "chromium-browser", "navigator", "firefox"})
# Fenêtres qui ne sont pas des applications de la personne.
HIDDEN_CLASSES = frozenset({"lxqt-panel", "sigildesk"})
# Applications ouvertes depuis les dossiers : (icône, nom court ; None = titre de la fenêtre).
KNOWN_APPS: dict[str, tuple[str, str | None]] = {
    "lximage-qt": ("photos", "Photo"),
    "vlc": ("videos", "Vidéo"),
    "mpv": ("videos", "Vidéo"),
    "qpdfview": ("pdf", "PDF"),
    "pcmanfm-qt": ("files", None),
}


@dataclass(frozen=True)
class OpenWindow:
    """Une ligne de `wmctrl -lxp`."""

    id: str  # « 0x0340000a », tel que wmctrl le réutilise pour -i -a
    desktop: int  # -1 : fenêtre du bureau (fond, panneau), à ignorer
    pid: int
    instance: str  # partie gauche de WM_CLASS
    wm_class: str  # partie droite de WM_CLASS
    title: str


def parse_wmctrl(output: str) -> list[OpenWindow]:
    """Lit `wmctrl -lxp` : id, bureau, pid, instance.classe, machine, titre."""
    windows: list[OpenWindow] = []
    for line in output.splitlines():
        parts = line.split(None, 5)
        if len(parts) < 5 or not parts[0].startswith("0x"):
            continue
        try:
            desktop, pid = int(parts[1]), int(parts[2])
        except ValueError:
            continue
        instance, _, wm_class = parts[3].rpartition(".")
        title = parts[5] if len(parts) > 5 else ""
        windows.append(OpenWindow(parts[0], desktop, pid, instance or wm_class, wm_class, title))
    return windows


def host_matches(instance: str, host: str) -> bool:
    """Instance d'une fenêtre d'application Chromium : « www.youtube.com » ou
    « outlook.live.com__mail_ » (hôte, puis chemin)."""
    instance, host = instance.lower(), host.lower()
    return bool(host) and (instance == host or instance.startswith(host + "_"))


def describe(window: OpenWindow, app_hosts: Mapping[str, tuple[str, str]]) -> tuple[str, str]:
    """(nom court, icône) d'une fenêtre, pour la barre des fenêtres ouvertes.

    `app_hosts` : hôte des tuiles ouvertes en fenêtre d'application → (libellé,
    icône), par exemple « www.youtube.com » → (« YouTube », « youtube »).
    """
    instance = window.instance.lower()
    for host, (label, icon) in app_hosts.items():
        if host_matches(instance, host):
            return label, icon
    if instance in BROWSER_INSTANCES:
        return "Internet", "internet"
    app = KNOWN_APPS.get(window.wm_class.lower()) or KNOWN_APPS.get(instance)
    if app:
        icon, label = app
        return label or window.title or "Dossier", icon
    # Application inconnue : la partie du titre avant « — » ou « - » (souvent le document).
    title = window.title.split(" — ")[0].split(" - ")[0].strip()
    return title or window.wm_class, "fenetre"

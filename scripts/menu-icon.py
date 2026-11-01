#!/usr/bin/env python3
"""Icône du bouton de menu du panneau LXQt : pose ou retire l'icône Sigilys system.

Ne touche qu'au `panel.conf` de l'utilisateur (`~/.config/lxqt/panel.conf`),
et seulement aux clés `ownIcon` et `icon` des greffons de menu (`fancymenu`
sous Lubuntu 26.04, `mainmenu` ailleurs). LXQt fusionne ce fichier, clé par
clé, avec ceux du système (XDG_CONFIG_DIRS) : le greffon de menu est donc
cherché dans les deux, et seules nos deux clés sont écrites chez l'utilisateur.
Tout le reste du fichier utilisateur est recopié tel quel.

    python3 scripts/menu-icon.py poser /chemin/vers/icone.svg
    python3 scripts/menu-icon.py retirer

Le panneau est relancé par la session LXQt (D-Bus) ; sinon, l'icône change à
la prochaine ouverture de session.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

MENU_TYPES = ("fancymenu", "mainmenu")
MARK = "sigildesk"  # l'icône posée vit sous ~/.local/share/sigildesk/ : c'est notre signature


def config_home() -> Path:
    value = os.environ.get("XDG_CONFIG_HOME", "")
    return Path(value) if value.startswith("/") else Path.home() / ".config"


def system_panel_confs() -> list[Path]:
    dirs = os.environ.get("XDG_CONFIG_DIRS") or "/etc/xdg/xdg-Lubuntu:/etc/xdg"
    return [Path(folder) / "lxqt" / "panel.conf" for folder in dirs.split(":")
            if folder.startswith("/") and (Path(folder) / "lxqt" / "panel.conf").is_file()]


def menu_sections(lines: list[str]) -> set[str]:
    """Noms des sections dont `type=` est un greffon de menu."""
    found, section = set(), None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1]
        elif (section and stripped.replace(" ", "").startswith("type=")
              and stripped.split("=", 1)[1].strip() in MENU_TYPES):
            found.add(section)
    return found


def _section_of(lines: list[str]) -> list[str | None]:
    """Section de chaque ligne (None avant la première)."""
    sections, current = [], None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current = stripped[1:-1]
        sections.append(current)
    return sections


def _key(line: str) -> str:
    return line.strip().split("=", 1)[0].strip()


def rewrite(lines: list[str], icon: str | None, targets: set[str]) -> list[str]:
    """Avec `icon` : remplace ownIcon/icon des menus `targets` par les nôtres, juste
    sous l'en-tête (section créée si le fichier utilisateur ne l'a pas). Sans :
    retire ownIcon/icon des seuls menus dont l'icône est la nôtre."""
    sections = _section_of(lines)
    ours = {s for line, s in zip(lines, sections, strict=True)
            if s in targets and _key(line) == "icon" and MARK in line}
    touched = targets if icon else ours
    out = []
    for line, section in zip(lines, sections, strict=True):
        if section in touched and _key(line) in ("ownIcon", "icon"):
            continue
        out.append(line)
        stripped = line.strip()
        if icon and section in touched and stripped == f"[{section}]":
            out += ["ownIcon=true\n", f"icon={icon}\n"]
    if icon:
        for section in sorted(targets - set(sections)):
            if out and out[-1].strip():
                out.append("\n")
            out += [f"[{section}]\n", "ownIcon=true\n", f"icon={icon}\n"]
    return out


def write_atomic(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".panel-", dir=path.parent)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.writelines(lines)
    os.replace(tmp, path)


def _panel_running() -> bool:
    done = subprocess.run(["pgrep", "-u", str(os.getuid()), "-x", "lxqt-panel"], capture_output=True, check=False)
    return done.returncode == 0


def _wait(condition, seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.2)
    return condition()


def restart_panel() -> bool:
    """Relance le panneau par la session LXQt ; faux si ce n'est pas possible ici.

    stopModule rend la main avant que le panneau soit fermé : relancer aussitôt
    échoue en silence et le panneau disparaît (vu dans la VM le 2026-10-28). On
    attend donc sa fermeture, puis on vérifie qu'il est bien revenu.
    """
    dbus = shutil.which("dbus-send")
    if not dbus or "lxqt" not in os.environ.get("XDG_CURRENT_DESKTOP", "").lower():
        return False

    def call(method: str) -> bool:
        done = subprocess.run([dbus, "--session", "--print-reply", "--dest=org.lxqt.session", "/LXQtSession",
                               f"org.lxqt.session.{method}", "string:lxqt-panel.desktop"],
                              capture_output=True, text=True, timeout=10, check=False)
        return done.returncode == 0

    if not call("stopModule"):
        return False
    _wait(lambda: not _panel_running(), 8)
    for _ in range(3):
        call("startModule")
        if _wait(_panel_running, 5):
            return True
    return False


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] not in ("poser", "retirer") or (argv[1] == "poser" and len(argv) != 3):
        print(__doc__)
        return 64
    user_conf = config_home() / "lxqt" / "panel.conf"
    lines = user_conf.read_text(encoding="utf-8").splitlines(keepends=True) if user_conf.is_file() else []
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    targets = menu_sections(lines)
    for system in system_panel_confs():
        targets |= menu_sections(system.read_text(encoding="utf-8").splitlines())
    if not targets:
        print("Pas de bouton de menu dans le panneau : rien à faire.")
        return 0
    icon = str(Path(argv[2]).resolve()) if argv[1] == "poser" else None
    if icon and not Path(icon).is_file():
        print(f"Icône introuvable : {icon}", file=sys.stderr)
        return 1
    new = rewrite(lines, icon, targets)
    if new == lines:
        print("Icône du menu déjà à jour." if icon else "Icône du menu d'origine déjà en place.")
        return 0
    write_atomic(user_conf, new)
    print("Icône du menu Sigilys posée." if icon else "Icône du menu d'origine rétablie.")
    if restart_panel():
        print("Panneau relancé.")
    else:
        print("Effet à la prochaine ouverture de session.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

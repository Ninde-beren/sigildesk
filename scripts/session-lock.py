#!/usr/bin/env python3
"""Verrouillage de l'écran avant la mise en veille (LXQt) : le couper s'il ne peut pas marcher.

Par défaut, LXQt verrouille l'écran avant une mise en veille avec
`xdg-screensaver lock`. Sans écran de verrouillage installé (xscreensaver
n'est que « recommandé » par Lubuntu 26.04), cela échoue et affiche « Erreur de
l'économiseur d'écran » à chaque réveil. C'est l'« option 1 » retenue par
Antoine le 2026-10-28 : pas de verrouillage, on retrouve directement l'accueil.

    python3 scripts/session-lock.py couper     # seulement si aucun verrouilleur n'est installé
    python3 scripts/session-lock.py retablir   # annule, seulement si c'est SigilDesk qui l'a coupé

Même réglage que la case de Préférences LXQt › Paramètres de session :
`lock_screen_before_power_actions` dans [General] de ~/.config/lxqt/session.conf.
Le reste du fichier est recopié tel quel. Un fichier témoin dans les données de
SigilDesk garde trace du changement, pour ne défaire que le nôtre.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

KEY = "lock_screen_before_power_actions"
LOCKERS = ("xscreensaver", "light-locker", "xsecurelock", "i3lock", "slock", "xlock")


def _xdg(variable: str, fallback: str) -> Path:
    value = os.environ.get(variable, "")
    return Path(value) if value.startswith("/") else Path.home() / fallback


def session_conf() -> Path:
    return _xdg("XDG_CONFIG_HOME", ".config") / "lxqt" / "session.conf"


def marker() -> Path:
    return _xdg("XDG_DATA_HOME", ".local/share") / "sigildesk" / "verrouillage-coupe"


def set_general(lines: list[str], key: str, value: str | None) -> list[str]:
    """Pose (ou retire, si `value` est None) `key` dans [General], sans toucher au reste."""
    out, section, done = [], None, False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if section == "General" and value is not None and not done:
                blanks = []
                while out and not out[-1].strip():  # la clé va avant la ligne vide qui clôt la section
                    blanks.insert(0, out.pop())
                out += [f"{key}={value}\n"] + blanks
                done = True
            section = stripped[1:-1]
            out.append(line)
            continue
        if section == "General" and stripped.split("=", 1)[0].strip() == key:
            if value is not None and not done:
                out.append(f"{key}={value}\n")
                done = True
            continue
        out.append(line)
    if value is not None and not done:
        if section == "General":
            out.append(f"{key}={value}\n")
        else:
            out = ["[General]\n", f"{key}={value}\n", "\n"] + out
    return out


def write_atomic(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".session-", dir=path.parent)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.writelines(lines)
    os.replace(tmp, path)


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in ("couper", "retablir"):
        print(__doc__)
        return 64
    conf = session_conf()
    lines = conf.read_text(encoding="utf-8").splitlines(keepends=True) if conf.is_file() else []
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"

    if argv[1] == "couper":
        locker = next((name for name in LOCKERS if shutil.which(name)), None)
        if locker:
            print(f"Verrouillage avant la veille conservé : {locker} est installé.")
            return 0
        new = set_general(lines, KEY, "false")
        if new != lines:
            write_atomic(conf, new)
            marker().parent.mkdir(parents=True, exist_ok=True)
            marker().write_text("SigilDesk a coupé lock_screen_before_power_actions (session.conf).\n",
                                encoding="utf-8")
            print("Verrouillage avant la veille coupé (aucun écran de verrouillage installé).")
        else:
            print("Verrouillage avant la veille déjà coupé.")
        return 0

    if not marker().exists():
        print("Verrouillage avant la veille : rien à rétablir.")
        return 0
    write_atomic(conf, set_general(lines, KEY, None))  # LXQt reprend sa valeur d'origine
    marker().unlink()
    print("Verrouillage avant la veille rétabli (valeur d'origine de LXQt).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

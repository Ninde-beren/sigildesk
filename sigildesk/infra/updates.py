"""Mises à jour du système, en lecture seule : SigilDesk observe, il n'installe rien.

Les mises à jour s'installent seules (unattended-upgrades, réglé par
`scripts/install-system-deps.sh` ; les snaps comme Chromium se mettent à jour
d'eux-mêmes). Ce module répond à deux questions : un redémarrage est-il
nécessaire, et les mises à jour automatiques sont-elles en place ? Le rappel à
l'utilisateur est dans `ui.update_monitor`.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Fichier posé par install-system-deps.sh : sa présence dit que les mises à
# jour automatiques complètes sont en place.
AUTO_UPDATES_CONF = "52sigildesk-mises-a-jour"


def kernel_version_key(version: str) -> tuple:
    """Clé de tri d'une version de noyau (« 6.17.0-14-generic »).

    Chaque morceau devient (0, nombre) ou (1, texte) : les nombres se comparent
    entre eux, les textes entre eux, et un nombre passe toujours avant un texte.
    Comparer directement des entiers à des chaînes lèverait `TypeError` dès que
    deux versions n'ont pas la même forme (« 6.17.0-14.1-generic »).
    """
    return tuple((0, int(part)) if part.isdigit() else (1, part) for part in re.split(r"[.\-+~]", version))


@dataclass(frozen=True)
class RebootCheck:
    required: bool
    packages: tuple[str, ...] = ()


def reboot_required(run_dir: Path = Path("/run"), boot_dir: Path = Path("/boot"),
                    running_kernel: str | None = None) -> RebootCheck:
    """Redémarrage nécessaire ? Deux signes, l'un ou l'autre suffit.

    1. `/run/reboot-required`, posé par update-notifier-common après une mise à
       jour du noyau, de la libc, de dbus…
    2. Un noyau plus récent installé dans /boot que celui qui tourne (même
       saveur : generic, lowlatency…).
    """
    flag = run_dir / "reboot-required"
    if flag.exists():
        try:
            packages = tuple(sorted(set((run_dir / "reboot-required.pkgs").read_text(encoding="utf-8").split())))
        except OSError:
            packages = ()
        return RebootCheck(True, packages)

    running = running_kernel or os.uname().release
    try:
        installed = [p.name[len("vmlinuz-"):] for p in boot_dir.glob("vmlinuz-*")]
    except OSError:
        installed = []
    flavour = running.rsplit("-", 1)[-1] if "-" in running else ""
    same_flavour = [v for v in installed if not flavour or v.endswith("-" + flavour)]
    if same_flavour:
        newest = max(same_flavour, key=kernel_version_key)
        if kernel_version_key(newest) > kernel_version_key(running):
            return RebootCheck(True, (f"linux {newest}",))
    return RebootCheck(False)


@dataclass(frozen=True)
class AutoUpdates:
    enabled: bool
    last_run: datetime | None


def auto_updates_status(apt_conf_dir: Path = Path("/etc/apt/apt.conf.d"),
                        stamp: Path = Path("/var/lib/apt/periodic/unattended-upgrades-stamp")) -> AutoUpdates:
    """Réglage posé par SigilDesk présent ? Date de la dernière passe d'unattended-upgrades ?"""
    enabled = (apt_conf_dir / AUTO_UPDATES_CONF).is_file()
    try:
        last = datetime.fromtimestamp(stamp.stat().st_mtime).astimezone()
    except OSError:
        last = None
    return AutoUpdates(enabled, last)

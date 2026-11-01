"""Programmes extérieurs : les trouver, les lancer, lire leur sortie. Jamais de shell.

Trois opérations, toutes à arguments séparés :

- `find_program` : chemin absolu d'un programme (PATH, puis /snap/bin, absent du
  PATH de certaines sessions alors que Chromium y est) ;
- `start_detached` : lance un programme qui survit à SigilDesk (navigateur,
  explorateur, `dbus-send`), via `QProcess.startDetached` ;
- `run_capture` : lance un utilitaire court (`wmctrl`, `xdg-mime`, `dbus-send
  --print-reply`) et renvoie sa sortie standard, ou None s'il échoue ou traîne.

Les modules qui les utilisent les reçoivent en paramètre (`which`, `starter`,
`runner`), ce qui permet aux tests de les remplacer par des fonctions pures.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

SNAP_BIN = Path("/snap/bin")


def find_program(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    candidate = SNAP_BIN / name
    return str(candidate) if candidate.is_file() and os.access(candidate, os.X_OK) else None


def start_detached(program: str, args: list[str], workdir: str | None = None) -> bool:
    from PySide6.QtCore import QProcess  # import local : les tests du domaine n'ont pas besoin de Qt

    result = QProcess.startDetached(program, args, workdir) if workdir else QProcess.startDetached(program, args)
    # PySide6 renvoie (succès, pid) ; certaines versions un booléen seul.
    return bool(result[0] if isinstance(result, tuple) else result)


def run_capture(argv: list[str], timeout: float = 4) -> str | None:
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None

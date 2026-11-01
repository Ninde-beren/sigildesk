"""Écriture atomique de fichiers JSON : jamais de fichier à moitié écrit.

Le document est écrit dans un fichier temporaire du même dossier, synchronisé
sur le disque, puis renommé par-dessus la cible (`os.replace`, atomique sur un
même système de fichiers). Une coupure de courant laisse donc l'ancien fichier
intact ou le nouveau complet, jamais un mélange.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


def atomic_write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.stem}-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(document, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise

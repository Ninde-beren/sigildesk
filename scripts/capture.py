#!/usr/bin/env python3
"""Captures réelles de SigilDesk (rendu Qt hors écran), dans docs/captures/.

Chaque capture est produite par l'application elle-même (`--screenshot`), avec
une configuration jetable : rien n'est dessiné à part.

    python3 scripts/capture.py [dossier_de_sortie]
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

TOURS = {"name": "Tours", "region": "Centre-Val de Loire", "country": "France",
         "latitude": 47.39484, "longitude": 0.70398}

# fichier, taille, confort, fond, panneau, noms sous les icônes[, fenêtres ouvertes imaginaires]
SHOTS = [
    ("accueil-fenetres-ouvertes.png", "1366x768", False, "aube", None, True, "youtube,images"),
    ("accueil-1366x768.png", "1366x768", False, "aube", None, True),
    ("accueil-1366x768-confort.png", "1366x768", True, "aube", None, True),
    ("accueil-sans-noms.png", "1366x768", False, "aube", None, False),
    ("accueil-1024x600.png", "1024x600", False, "aurore", None, True),
    ("accueil-1024x600-confort.png", "1024x600", True, "aurore", None, True),
    ("accueil-fond-sombre.png", "1366x768", False, "blueprint", None, True),
    ("favoris.png", "1366x768", False, "aube", "favoris", True),
    ("favori-ajout.png", "1366x768", False, "aube", "editeur", True),
    ("parametres.png", "1366x768", False, "aube", "parametres", True),
    ("parametres-confort.png", "1366x768", True, "orbite", "parametres", True),
    ("dossiers.png", "1366x768", False, "aube", "dossiers", True),
    ("meteo.png", "1366x768", False, "aube", "meteo", True),
    ("a-propos.png", "1366x768", False, "aube", "apropos", True),
    ("fond-ecran.png", "1366x768", False, "orbite", "fonds", True),
    ("eteindre.png", "1366x768", False, "aube", "eteindre", True),
]


def main() -> int:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "docs" / "captures"
    out_dir.mkdir(parents=True, exist_ok=True)
    venv_python = REPO / ".venv/bin/python"
    python = os.environ.get("SIGILDESK_PYTHON") or (str(venv_python) if venv_python.exists() else sys.executable)
    defaults = json.loads((REPO / "config" / "default.json").read_text(encoding="utf-8"))
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    for name, size, comfort, wallpaper, panel, labels, *windows in SHOTS:
        with tempfile.TemporaryDirectory(prefix="sigildesk-capture-") as tmp:
            doc = json.loads(json.dumps(defaults))
            doc["appearance"].update(comfort=comfort, wallpaper=wallpaper, show_labels=labels)
            doc["user_name"] = "Marie"
            doc["web"]["mail"] = {"provider": "orange", "url": ""}
            doc["weather"]["city"] = TOURS  # météo réelle, demandée à Open-Meteo au moment de la capture
            (Path(tmp) / "config").mkdir()
            (Path(tmp) / "config" / "config.json").write_text(json.dumps(doc), encoding="utf-8")
            argv = [python, "-m", "sigildesk", "--root", tmp, "--size", size, "--screenshot", str(out_dir / name)]
            if panel:
                argv += ["--panel", panel]
            if windows:
                argv += ["--fenetres-essai", windows[0]]
            done = subprocess.run(argv, cwd=REPO, env=env, capture_output=True, text=True, timeout=120)
            status = "ok" if done.returncode == 0 and (out_dir / name).exists() else f"ÉCHEC\n{done.stderr[-1500:]}"
            print(f"{name:34} {status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

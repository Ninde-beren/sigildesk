"""Options de la ligne de commande. Les options sans tiret particulier servent au développement et aux tests."""

from __future__ import annotations

import argparse
from pathlib import Path

from sigildesk import APP_NAME, __version__

PANELS = ("favoris", "parametres", "fonds", "eteindre", "editeur", "meteo", "apropos", "redemarrer", "maintenance")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="sigildesk", description="Accueil simplifié pour Lubuntu/LXQt.")
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {__version__}")
    parser.add_argument("--windowed", action="store_true", help="fenêtre au lieu du plein écran (développement)")
    parser.add_argument("--size", default="1366x768", help="taille de la fenêtre, ex. 1024x600")
    parser.add_argument("--software", action="store_true", help="rendu logiciel, si l'affichage reste noir")
    parser.add_argument("--root", type=Path, help="regroupe config, données et journaux sous ce dossier (essais)")
    parser.add_argument("--doctor", action="store_true", help="vérifie les dépendances et quitte")
    parser.add_argument("--autostart", action="store_true", help="lancé par l'autostart de la session")
    parser.add_argument("--print-ready", action="store_true", help="affiche SIGILDESK_READY quand l'accueil est prêt")
    parser.add_argument("--screenshot", type=Path, help="enregistre une capture de la fenêtre puis quitte")
    parser.add_argument("--panel", choices=PANELS, help="panneau ouvert pour la capture")
    parser.add_argument("--no-network", action="store_true",
                        help="aucune requête réseau (tests) : météo depuis le cache seulement")
    parser.add_argument("--fenetres-essai", default="",
                        help="fenêtres imaginaires pour captures et tests, ex. youtube,images,vlc")
    parser.add_argument("--dump-geometry", type=Path, help="écrit la géométrie des zones (tests) puis quitte")
    args = parser.parse_args(argv)
    try:
        width, height = (int(v) for v in args.size.lower().split("x"))
    except ValueError:
        parser.error("--size attend LARGEURxHAUTEUR, par exemple 1366x768")
    args.width, args.height = width, height
    args.capture = args.screenshot is not None or args.dump_geometry is not None
    return args

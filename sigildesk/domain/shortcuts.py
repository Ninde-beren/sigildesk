"""Raccourci de maintenance (`Ctrl+Alt+M` par défaut) : validation et conflits.

Le raccourci réduit SigilDesk pour retrouver le bureau LXQt. Deux règles :

- il exige deux modificateurs parmi Ctrl, Alt et Meta, pour qu'une personne
  novice ne le déclenche pas par hasard ;
- il ne doit pas être déjà pris par un raccourci global de LXQt, qui le
  capterait avant SigilDesk et le rendrait muet. `find_conflicts` lit pour
  cela le contenu d'un `globalkeyshortcuts.conf` ; la lecture des fichiers
  eux-mêmes est dans `infra.lxqt`.
"""

from __future__ import annotations

import configparser
from urllib.parse import unquote

DEFAULT_SHORTCUT = "Ctrl+Alt+M"

# Ordre canonique des modificateurs dans la forme normalisée.
_MODIFIERS = ("Ctrl", "Alt", "Shift", "Meta")
_ALIASES = {
    "control": "Ctrl", "ctrl": "Ctrl", "alt": "Alt", "shift": "Shift",
    "meta": "Meta", "super": "Meta", "win": "Meta",
}
_KEYS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") | {f"F{n}" for n in range(1, 13)}


class ShortcutError(ValueError):
    """Raccourci refusé ; le message dit pourquoi, en français."""


def validate_shortcut(text: object) -> str:
    """Normalise « ctrl+alt+m » en « Ctrl+Alt+M », ou lève `ShortcutError`."""
    if not isinstance(text, str) or not text.strip():
        raise ShortcutError("raccourci vide")
    parts = [part.strip() for part in text.split("+")]
    if any(not part for part in parts):
        raise ShortcutError("raccourci mal formé")
    *modifiers, key = parts

    found: list[str] = []
    for modifier in modifiers:
        name = _ALIASES.get(modifier.lower())
        if name is None:
            raise ShortcutError(f"modificateur inconnu « {modifier} »")
        if name in found:
            raise ShortcutError(f"modificateur répété « {modifier} »")
        found.append(name)

    key = key.upper()
    if key not in _KEYS:
        raise ShortcutError("touche attendue : une lettre, un chiffre ou F1 à F12")
    if sum(name in ("Ctrl", "Alt", "Meta") for name in found) < 2:
        raise ShortcutError("deux modificateurs parmi Ctrl, Alt et Meta sont nécessaires")
    return "+".join([name for name in _MODIFIERS if name in found] + [key])


def find_conflicts(ini_text: str, shortcut: str, source: str = "") -> list[str]:
    """Raccourcis LXQt actifs égaux à `shortcut` dans un `globalkeyshortcuts.conf`.

    Les sections ont la forme « Control%2BAlt%2BT.12 » (combinaison encodée,
    puis un numéro). Chaque conflit est décrit par son commentaire ou sa
    commande, suivi de `source` (le fichier d'origine) s'il est donné.
    """
    wanted = validate_shortcut(shortcut)
    parser = configparser.RawConfigParser(strict=False, interpolation=None)
    try:
        parser.read_string(ini_text)
    except configparser.Error:
        return []

    conflicts: list[str] = []
    for section in parser.sections():
        combo = unquote(section).rsplit(".", 1)[0]
        try:
            normalized = validate_shortcut(combo)
        except ShortcutError:
            continue  # section qui n'est pas un raccourci, ou raccourci à un seul modificateur
        if normalized != wanted:
            continue
        if parser.get(section, "Enabled", fallback="true").strip().lower() == "false":
            continue
        what = parser.get(section, "Comment", fallback="") or parser.get(section, "Exec", fallback="") or section
        conflicts.append(f"{what} ({source})" if source else what)
    return conflicts

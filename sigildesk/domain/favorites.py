"""« Mes favoris » : la règle d'un favori valide.

Un favori est un nom court, une adresse web normalisée et l'un des pictogrammes
livrés (`catalog.FAVORITE_ICONS`) ; aucun favicon n'est jamais téléchargé. Le
modèle Qt qui porte la liste est `ui.favorites_model`.
"""

from __future__ import annotations

from sigildesk.domain import catalog
from sigildesk.domain.urls import UrlError, normalize_web_url


class FavoriteError(ValueError):
    """Favori refusé ; le message s'adresse à l'utilisateur."""


def validate_favorite(name: str, url: str, icon: str) -> dict:
    """Favori prêt à enregistrer (`name`, `url`, `icon`), ou `FavoriteError`.

    Un pictogramme inconnu n'est pas une erreur : le premier de la liste le
    remplace, pour qu'un favori ne soit jamais perdu pour une icône.
    """
    name = (name or "").strip()
    if not name:
        raise FavoriteError("Donnez un nom à ce favori.")
    if len(name) > catalog.MAX_FAVORITE_NAME:
        raise FavoriteError(f"Le nom doit faire {catalog.MAX_FAVORITE_NAME} caractères au plus.")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in name):
        raise FavoriteError("Le nom contient un caractère non valide.")
    try:
        clean_url = normalize_web_url(url or "")
    except UrlError as exc:
        raise FavoriteError(str(exc)) from exc
    if icon not in catalog.FAVORITE_ICON_IDS:
        icon = catalog.FAVORITE_ICON_IDS[0]
    return {"name": name, "url": clean_url, "icon": icon}

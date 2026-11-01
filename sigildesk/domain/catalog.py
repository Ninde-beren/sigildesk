"""Ce que SigilDesk propose, fixé dans le code : tuiles, messageries, dossiers, pictogrammes.

La configuration JSON ne fait que choisir parmi ces listes. Elle ne contient
jamais de commande : les programmes lancés sont décidés dans `domain.commands`.
Ajouter une tuile, une messagerie ou un pictogramme se fait ici (et, pour une
icône, dans `resources/icons/`).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TileSpec:
    id: str
    label: str
    icon: str
    section: str  # "web" ou "local"
    hint: str
    app_window: bool = False  # avec Chromium : fenêtre sans barre d'adresse


TILES: tuple[TileSpec, ...] = (
    TileSpec("internet", "Internet", "internet", "web", "Ouvrir le navigateur"),
    TileSpec("facebook", "Facebook", "facebook", "web", "Ouvrir Facebook", app_window=True),
    TileSpec("mail", "Mails", "mail", "web", "Ouvrir ma messagerie", app_window=True),
    TileSpec("youtube", "YouTube", "youtube", "web", "Ouvrir YouTube", app_window=True),
    TileSpec("files", "Fichiers", "files", "local", "Ouvrir mes fichiers"),
    TileSpec("photos", "Photos", "photos", "local", "Ouvrir le dossier Images"),
    TileSpec("videos", "Vidéos", "videos", "local", "Ouvrir le dossier Vidéos"),
    TileSpec("pdf", "PDF", "pdf", "local", "Ouvrir mes documents PDF"),
)
TILE_IDS = tuple(tile.id for tile in TILES)
WEB_TILE_IDS = tuple(tile.id for tile in TILES if tile.section == "web")
LOCAL_TILE_IDS = tuple(tile.id for tile in TILES if tile.section == "local")
_TILES_BY_ID = {tile.id: tile for tile in TILES}


def tile(tile_id: str) -> TileSpec | None:
    return _TILES_BY_ID.get(tile_id)


@dataclass(frozen=True)
class MailProvider:
    id: str
    label: str
    url: str


# Adresses vérifiées le 2026-10-27 (réponse HTTP 200 après redirections).
# Aucune n'est choisie par défaut : la messagerie se règle dans Paramètres.
MAIL_PROVIDERS: tuple[MailProvider, ...] = (
    MailProvider("gmail", "Gmail", "https://mail.google.com/"),
    MailProvider("outlook", "Outlook / Hotmail", "https://outlook.live.com/mail/"),
    MailProvider("orange", "Orange", "https://messagerie.orange.fr/"),
    MailProvider("free", "Free", "https://webmail.free.fr/"),
    MailProvider("sfr", "SFR", "https://webmail.sfr.fr/"),
    MailProvider("laposte", "La Poste", "https://www.laposte.net/accueil"),
    MailProvider("yahoo", "Yahoo", "https://mail.yahoo.com/"),
)
MAIL_PROVIDER_IDS = tuple(provider.id for provider in MAIL_PROVIDERS)
MAIL_CUSTOM = "autre"


def mail_provider(provider_id: str) -> MailProvider | None:
    return next((p for p in MAIL_PROVIDERS if p.id == provider_id), None)


# Dossiers que les tuiles locales peuvent ouvrir (clés des dossiers XDG).
FOLDER_KEYS = ("home", "desktop", "documents", "downloads", "pictures", "videos", "music")
FOLDER_LABELS = {
    "home": "Dossier personnel",
    "desktop": "Bureau",
    "documents": "Documents",
    "downloads": "Téléchargements",
    "pictures": "Images",
    "videos": "Vidéos",
    "music": "Musique",
}

# Pictogrammes livrés pour les favoris ; aucun favicon n'est téléchargé.
FAVORITE_ICONS: tuple[tuple[str, str], ...] = (
    ("fav-etoile", "Étoile"),
    ("fav-actualites", "Actualités"),
    ("fav-meteo", "Météo"),
    ("fav-achats", "Achats"),
    ("fav-banque", "Banque"),
    ("fav-sante", "Santé"),
    ("fav-musique", "Musique"),
    ("fav-carte", "Carte"),
    ("fav-cuisine", "Cuisine"),
    ("fav-video", "Vidéo"),
    ("fav-jeux", "Jeux"),
    ("fav-demarches", "Démarches"),
)
FAVORITE_ICON_IDS = tuple(icon for icon, _ in FAVORITE_ICONS)
MAX_FAVORITES = 12
MAX_FAVORITE_NAME = 32
MAX_USER_NAME = 30

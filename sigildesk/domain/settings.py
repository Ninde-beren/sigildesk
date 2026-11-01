"""Schéma des réglages : validation stricte et migrations, sans toucher au disque.

Le fichier (`~/.config/sigildesk/config.json`, lu et écrit par
`infra.config_store`) suit un schéma **fermé** : une clé inconnue, un type
inattendu ou une valeur hors liste rendent le document invalide, et `validate`
renvoie une copie normalisée (adresses canoniques, textes épurés, adresse de
messagerie recopiée du catalogue). Le JSON ne contient jamais de commande :
seulement des choix parmi `catalog` et des adresses http(s).

Faire évoluer le schéma : ajouter la clé dans `config/default.json` et dans
`validate`, incrémenter `SCHEMA_VERSION`, puis écrire dans `MIGRATIONS` la
fonction qui fait monter un document de la version précédente.
"""

from __future__ import annotations

import copy
import re
from typing import Any

from sigildesk.domain import catalog
from sigildesk.domain.shortcuts import ShortcutError, validate_shortcut
from sigildesk.domain.urls import UrlError, normalize_web_url

SCHEMA_VERSION = 2
BROWSERS = ("auto", "chromium", "firefox", "systeme")
WINDOW_MODES = ("plein-ecran", "fenetre")
_WALLPAPER_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


class ConfigError(ValueError):
    """Document de configuration refusé ; `str()` donne le chemin fautif."""


# --- Briques de validation ---------------------------------------------------------
# Chacune reçoit la valeur et son chemin (« web.mail.url ») pour un message précis.

def _object(value: Any, path: str, keys: tuple[str, ...]) -> dict:
    if not isinstance(value, dict):
        raise ConfigError(f"{path} : un objet est attendu")
    missing = [key for key in keys if key not in value]
    extra = [key for key in value if key not in keys]
    if missing:
        raise ConfigError(f"{path} : clé manquante « {missing[0]} »")
    if extra:
        raise ConfigError(f"{path} : clé inconnue « {extra[0]} »")
    return value


def _text(value: Any, path: str, max_len: int, allow_empty: bool = True) -> str:
    if not isinstance(value, str):
        raise ConfigError(f"{path} : un texte est attendu")
    value = value.strip()
    if not allow_empty and not value:
        raise ConfigError(f"{path} : ne doit pas être vide")
    if len(value) > max_len:
        raise ConfigError(f"{path} : {max_len} caractères au plus")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ConfigError(f"{path} : caractère de contrôle interdit")
    return value


def _choice(value: Any, path: str, choices: tuple[str, ...]) -> str:
    if not isinstance(value, str) or value not in choices:
        raise ConfigError(f"{path} : valeur attendue parmi {', '.join(choices)}")
    return value


def _bool(value: Any, path: str) -> bool:
    if type(value) is not bool:  # `isinstance` accepterait 0 et 1
        raise ConfigError(f"{path} : vrai ou faux attendu")
    return value


def _number(value: Any, path: str, low: float, high: float) -> float:
    if type(value) not in (int, float) or not low <= value <= high:
        raise ConfigError(f"{path} : nombre entre {low} et {high} attendu")
    return float(value)


def _url(value: Any, path: str) -> str:
    if not isinstance(value, str):
        raise ConfigError(f"{path} : une adresse est attendue")
    try:
        return normalize_web_url(value)
    except UrlError as exc:
        raise ConfigError(f"{path} : {exc}") from exc


def _mail(value: Any, path: str) -> dict:
    doc = _object(value, path, ("provider", "url"))
    choices = ("",) + catalog.MAIL_PROVIDER_IDS + (catalog.MAIL_CUSTOM,)
    provider = _choice(doc["provider"], f"{path}.provider", choices)
    if provider == "":
        if doc["url"] != "":
            raise ConfigError(f"{path}.url : doit rester vide tant qu'aucune messagerie n'est choisie")
        return {"provider": "", "url": ""}
    if provider == catalog.MAIL_CUSTOM:
        return {"provider": provider, "url": _url(doc["url"], f"{path}.url")}
    # Fournisseur connu : l'adresse vient du catalogue, jamais du fichier.
    return {"provider": provider, "url": catalog.mail_provider(provider).url}


def _weather(value: Any, path: str) -> dict:
    doc = _object(value, path, ("enabled", "city"))
    city = doc["city"]
    if city is not None:
        city = _object(city, f"{path}.city", ("name", "region", "country", "latitude", "longitude"))
        city = {
            "name": _text(city["name"], f"{path}.city.name", 80, allow_empty=False),
            "region": _text(city["region"], f"{path}.city.region", 80),
            "country": _text(city["country"], f"{path}.city.country", 60),
            "latitude": _number(city["latitude"], f"{path}.city.latitude", -90, 90),
            "longitude": _number(city["longitude"], f"{path}.city.longitude", -180, 180),
        }
    return {"enabled": _bool(doc["enabled"], f"{path}.enabled"), "city": city}


def _favorite(value: Any, path: str) -> dict:
    doc = _object(value, path, ("name", "url", "icon"))
    return {
        "name": _text(doc["name"], f"{path}.name", catalog.MAX_FAVORITE_NAME, allow_empty=False),
        "url": _url(doc["url"], f"{path}.url"),
        "icon": _choice(doc["icon"], f"{path}.icon", catalog.FAVORITE_ICON_IDS),
    }


# --- Document complet -------------------------------------------------------------

TOP_LEVEL_KEYS = (
    "schema_version", "user_name", "browser", "web", "folders", "appearance", "favorites", "maintenance", "window",
    "weather",
)


def validate(document: Any) -> dict:
    """Renvoie une copie normalisée du document, ou lève `ConfigError`."""
    doc = _object(document, "configuration", TOP_LEVEL_KEYS)
    if type(doc["schema_version"]) is not int or doc["schema_version"] != SCHEMA_VERSION:
        raise ConfigError(f"schema_version : {SCHEMA_VERSION} attendu")

    web = _object(doc["web"], "web", ("internet", "facebook", "mail", "youtube"))
    folders = _object(doc["folders"], "folders", catalog.LOCAL_TILE_IDS)
    appearance = _object(doc["appearance"], "appearance", ("comfort", "wallpaper", "show_labels"))
    maintenance = _object(doc["maintenance"], "maintenance", ("shortcut",))
    window = _object(doc["window"], "window", ("mode",))

    favorites = doc["favorites"]
    if not isinstance(favorites, list):
        raise ConfigError("favorites : une liste est attendue")
    if len(favorites) > catalog.MAX_FAVORITES:
        raise ConfigError(f"favorites : {catalog.MAX_FAVORITES} favoris au plus")

    wallpaper = appearance["wallpaper"]
    if not isinstance(wallpaper, str) or not _WALLPAPER_ID.match(wallpaper):
        raise ConfigError("appearance.wallpaper : identifiant de fond d'écran invalide")
    try:
        shortcut = validate_shortcut(maintenance["shortcut"])
    except ShortcutError as exc:
        raise ConfigError(f"maintenance.shortcut : {exc}") from exc

    return {
        "schema_version": SCHEMA_VERSION,
        "user_name": _text(doc["user_name"], "user_name", catalog.MAX_USER_NAME),
        "browser": _choice(doc["browser"], "browser", BROWSERS),
        "web": {
            "internet": _url(web["internet"], "web.internet"),
            "facebook": _url(web["facebook"], "web.facebook"),
            "mail": _mail(web["mail"], "web.mail"),
            "youtube": _url(web["youtube"], "web.youtube"),
        },
        "folders": {key: _choice(folders[key], f"folders.{key}", catalog.FOLDER_KEYS)
                    for key in catalog.LOCAL_TILE_IDS},
        "appearance": {
            "comfort": _bool(appearance["comfort"], "appearance.comfort"),
            "wallpaper": wallpaper,
            "show_labels": _bool(appearance["show_labels"], "appearance.show_labels"),
        },
        "favorites": [_favorite(item, f"favorites[{i}]") for i, item in enumerate(favorites)],
        "maintenance": {"shortcut": shortcut},
        "window": {"mode": _choice(window["mode"], "window.mode", WINDOW_MODES)},
        "weather": _weather(doc["weather"], "weather"),
    }


# --- Migrations ------------------------------------------------------------------

def _v1_to_v2(doc: dict) -> dict:
    # v2 (2026-10-28) : module météo (affiché, sans ville choisie) et noms sous les icônes (affichés).
    doc.setdefault("weather", {"enabled": True, "city": None})
    if isinstance(doc.get("appearance"), dict):
        doc["appearance"].setdefault("show_labels", True)
    return doc


# version de départ → fonction qui produit la version suivante
MIGRATIONS = {1: _v1_to_v2}


def migrate(document: Any) -> Any:
    """Fait monter un document ancien jusqu'à SCHEMA_VERSION ; le reste ne change pas."""
    if not isinstance(document, dict):
        return document
    document = copy.deepcopy(document)
    version = document.get("schema_version")
    while type(version) is int and version in MIGRATIONS:
        document = MIGRATIONS[version](document)
        version += 1
        document["schema_version"] = version
    return document

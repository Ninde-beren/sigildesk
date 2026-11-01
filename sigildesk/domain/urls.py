"""Validation des adresses web : seules les adresses http et https sortent d'ici.

Toute adresse passée au navigateur est d'abord normalisée par
`normalize_web_url`. Le résultat commence toujours par `http://` ou `https://`,
il ne peut donc pas être pris pour une option de ligne de commande.
"""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit, urlunsplit

MAX_URL_LENGTH = 2048
_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_TLD = re.compile(r"^(?:[a-z]{2,63}|xn--[a-z0-9-]{1,59})$")


class UrlError(ValueError):
    """Adresse refusée ; le message s'adresse à l'utilisateur, en français."""


def _check_host(host: str) -> str:
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None:
        return f"[{ip.compressed}]" if ip.version == 6 else ip.compressed
    try:
        ascii_host = host.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise UrlError("Le nom du site contient des caractères non valides.") from exc
    labels = ascii_host.rstrip(".").split(".")
    if len(labels) < 2 or len(ascii_host) > 253:
        raise UrlError("Il manque l'extension du site, par exemple « .fr » ou « .com ».")
    if not all(_LABEL.match(label) for label in labels) or not _TLD.match(labels[-1]):
        raise UrlError("Le nom du site contient des caractères non valides.")
    return host.lower().rstrip(".")


def normalize_web_url(text: str) -> str:
    """Valide une adresse saisie et la renvoie sous forme canonique.

    « meteofrance.com » devient « https://meteofrance.com/ ». Lève `UrlError`
    pour tout ce qui n'est pas une page web : javascript:, file:, data:,
    identifiants dans l'adresse, espaces, caractères de contrôle.
    """
    if not isinstance(text, str):
        raise UrlError("L'adresse doit être un texte.")
    value = text.strip()
    if not value:
        raise UrlError("L'adresse est vide.")
    if len(value) > MAX_URL_LENGTH:
        raise UrlError("L'adresse est trop longue.")
    if any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise UrlError("L'adresse ne doit pas contenir d'espace.")

    if "://" not in value:
        head = value.split("/", 1)[0]
        # « exemple.fr:8080 » est un port ; « javascript:… » ou « mailto:… » un autre schéma.
        if ":" in head and not head.rsplit(":", 1)[1].isdigit():
            raise UrlError("Seules les adresses de sites web (http ou https) sont acceptées.")
        value = "https://" + value

    parts = urlsplit(value)
    scheme = parts.scheme.lower()
    if scheme not in ("http", "https"):
        raise UrlError("Seules les adresses de sites web (http ou https) sont acceptées.")
    if parts.username is not None or parts.password is not None:
        raise UrlError("L'adresse ne doit pas contenir d'identifiant ni de mot de passe.")
    try:
        port = parts.port
    except ValueError as exc:
        raise UrlError("Le numéro de port de l'adresse n'est pas valide.") from exc
    if not parts.hostname:
        raise UrlError("Il manque le nom du site.")

    host = _check_host(parts.hostname)
    netloc = host if port is None else f"{host}:{port}"
    return urlunsplit((scheme, netloc, parts.path or "/", parts.query, parts.fragment))


def is_web_url(text: str) -> bool:
    try:
        normalize_web_url(text)
    except UrlError:
        return False
    return True


def display_host(url: str) -> str:
    """« https://www.meteofrance.com/x » → « meteofrance.com », pour les sous-titres."""
    host = urlsplit(url).hostname or ""
    return host[4:] if host.startswith("www.") else host

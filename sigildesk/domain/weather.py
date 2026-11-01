"""Météo, côté métier : ville, conditions, libellés. Indépendant du fournisseur et de Qt.

Un fournisseur (aujourd'hui `infra.open_meteo.OpenMeteo`) respecte le protocole
`WeatherProvider` : il fabrique les URL à appeler et traduit les réponses en
`City` et `Conditions`. Le changer ne touche ni au cache, ni au service, ni au
QML. Les libellés sont en français, la seule langue de SigilDesk.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Protocol


@dataclass(frozen=True)
class City:
    """Une ville choisie dans les résultats du géocodage."""

    name: str
    region: str
    country: str
    latitude: float
    longitude: float

    @property
    def label(self) -> str:
        """« Tours (Centre-Val de Loire, France) »."""
        details = ", ".join(part for part in (self.region, self.country) if part)
        return f"{self.name} ({details})" if details else self.name

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> City:
        return cls(str(data["name"]), str(data.get("region", "")), str(data.get("country", "")),
                   float(data["latitude"]), float(data["longitude"]))

    def same_place(self, other: City) -> bool:
        """Même lieu à ~100 m près : deux résultats de recherche peuvent différer au 4e décimal."""
        return (round(self.latitude, 3) == round(other.latitude, 3)
                and round(self.longitude, 3) == round(other.longitude, 3))


@dataclass(frozen=True)
class Conditions:
    """Conditions actuelles : température en °C, code météo WMO, jour ou nuit."""

    temperature: float
    code: int
    is_day: bool

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Conditions:
        temperature, code, is_day = data["temperature"], data["code"], data["is_day"]
        if type(temperature) not in (int, float) or type(code) is not int or type(is_day) is not bool:
            raise ValueError("conditions mal formées")
        return cls(float(temperature), code, is_day)


class ProviderError(Exception):
    """Réponse inexploitable du fournisseur ; le message s'adresse à l'utilisateur."""


class WeatherProvider(Protocol):
    """Ce qu'un fournisseur de météo doit savoir faire (sans effectuer lui-même les requêtes)."""

    name: str
    attribution: str
    attribution_url: str

    def current_url(self, city: City) -> str: ...
    def parse_current(self, data: object) -> Conditions: ...
    def search_url(self, query: str) -> str: ...
    def parse_search(self, data: object) -> list[City]: ...


# Codes WMO (norme 4677, utilisés par Open-Meteo) → (libellé, famille d'icône).
# Familles : soleil, eclaircies, nuages, brouillard, pluie, neige, orage.
_CODES: dict[int, tuple[str, str]] = {
    0: ("Ciel dégagé", "soleil"),
    1: ("Plutôt dégagé", "eclaircies"),
    2: ("Partiellement nuageux", "eclaircies"),
    3: ("Couvert", "nuages"),
    45: ("Brouillard", "brouillard"),
    48: ("Brouillard givrant", "brouillard"),
    51: ("Bruine légère", "pluie"),
    53: ("Bruine", "pluie"),
    55: ("Bruine dense", "pluie"),
    56: ("Bruine verglaçante", "pluie"),
    57: ("Bruine verglaçante", "pluie"),
    61: ("Pluie faible", "pluie"),
    63: ("Pluie", "pluie"),
    65: ("Forte pluie", "pluie"),
    66: ("Pluie verglaçante", "pluie"),
    67: ("Pluie verglaçante", "pluie"),
    71: ("Neige faible", "neige"),
    73: ("Neige", "neige"),
    75: ("Forte neige", "neige"),
    77: ("Grains de neige", "neige"),
    80: ("Averses", "pluie"),
    81: ("Averses", "pluie"),
    82: ("Fortes averses", "pluie"),
    85: ("Averses de neige", "neige"),
    86: ("Fortes averses de neige", "neige"),
    95: ("Orage", "orage"),
    96: ("Orage avec grêle", "orage"),
    99: ("Orage avec grêle", "orage"),
}


def describe(code: int, is_day: bool) -> tuple[str, str]:
    """(libellé français, nom de l'icône) ; la nuit, lune au lieu du soleil."""
    label, family = _CODES.get(code, ("Conditions inconnues", "nuages"))
    if code == 0 and is_day:
        label = "Ensoleillé"
    if family in ("soleil", "eclaircies") and not is_day:
        family = "lune" if family == "soleil" else "eclaircies-nuit"
    return label, f"meteo-{family}"


def format_temperature(value: float) -> str:
    """« 11 °C », « −3 °C » : arrondi, vrai signe moins (U+2212), espace fine insécable (U+202F)."""
    rounded = round(value) or 0  # `or 0` évite « −0 »
    sign = "\u2212" if rounded < 0 else ""
    return f"{sign}{abs(rounded)}\u202f°C"


def updated_label(fetched_at: datetime, now: datetime) -> str:
    """« Mis à jour à 14:05 », « … hier à 18:05 » ou « … le 25/10 à 08:00 »."""
    local, today = fetched_at.astimezone(now.tzinfo), now.date()
    hour = local.strftime("%H:%M")
    if local.date() == today:
        return f"Mis à jour à {hour}"
    if local.date() == today - timedelta(days=1):
        return f"Mis à jour hier à {hour}"
    return f"Mis à jour le {local.strftime('%d/%m')} à {hour}"

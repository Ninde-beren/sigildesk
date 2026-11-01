"""Cache local horodaté des dernières conditions météo (`~/.cache/sigildesk/meteo.json`).

Il sert à afficher quelque chose dès le démarrage et pendant une coupure de
connexion, avec l'heure de la dernière mise à jour. Un fichier abîmé, ou qui
concerne une autre ville, est simplement ignoré.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sigildesk.domain.weather import City, Conditions
from sigildesk.infra.files import atomic_write_json

log = logging.getLogger(__name__)
CACHE_VERSION = 1


@dataclass(frozen=True)
class CachedWeather:
    conditions: Conditions
    fetched_at: datetime  # avec fuseau horaire


class WeatherCache:
    def __init__(self, path: Path):
        self.path = path

    def load(self, city: City) -> CachedWeather | None:
        """Conditions enregistrées pour `city`, ou None (absentes, abîmées, autre ville)."""
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if data.get("version") != CACHE_VERSION:
                return None
            if not City.from_dict(data["city"]).same_place(city):
                return None
            fetched_at = datetime.fromisoformat(data["fetched_at"])
            if fetched_at.tzinfo is None:
                return None
            return CachedWeather(Conditions.from_dict(data["conditions"]), fetched_at)
        except FileNotFoundError:
            return None
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            log.warning("cache météo ignoré : %s", exc)
            return None

    def save(self, city: City, provider: str, conditions: Conditions, fetched_at: datetime) -> None:
        try:
            atomic_write_json(self.path, {
                "version": CACHE_VERSION,
                "provider": provider,
                "city": city.to_dict(),
                "fetched_at": fetched_at.isoformat(timespec="seconds"),
                "conditions": conditions.to_dict(),
            })
        except OSError as exc:
            log.warning("cache météo non enregistré : %s", exc)

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)

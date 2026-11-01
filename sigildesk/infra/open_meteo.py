"""Fournisseur Open-Meteo (https://open-meteo.com/), API gratuite, sans clé.

Conditions de l'API gratuite (vérifiées le 2026-10-28) : usage non commercial
uniquement, moins de 10 000 appels par jour, 5 000 par heure, 600 par minute,
et attribution des données sous licence CC BY 4.0. SigilDesk fait au plus 24
appels par jour. Un usage commercial impose un abonnement et une clé
(`customer-api.open-meteo.com`, même syntaxe d'appel).

Seules trois variables sont demandées : `temperature_2m`, `weather_code`, `is_day`.
"""

from __future__ import annotations

from urllib.parse import urlencode

from sigildesk.domain.weather import City, Conditions, ProviderError

MAX_RESULTS = 8


class OpenMeteo:
    name = "Open-Meteo"
    attribution = "Données météo : Open-Meteo.com (licence CC BY 4.0)"
    attribution_url = "https://open-meteo.com/"
    forecast_endpoint = "https://api.open-meteo.com/v1/forecast"
    geocoding_endpoint = "https://geocoding-api.open-meteo.com/v1/search"

    def current_url(self, city: City) -> str:
        query = urlencode({
            "latitude": f"{city.latitude:.4f}",
            "longitude": f"{city.longitude:.4f}",
            "current": "temperature_2m,weather_code,is_day",
            "timezone": "auto",
        })
        return f"{self.forecast_endpoint}?{query}"

    def parse_current(self, data: object) -> Conditions:
        _raise_api_error(data)
        current = data.get("current") if isinstance(data, dict) else None
        if not isinstance(current, dict):
            raise ProviderError("Réponse météo incomplète.")
        temperature, code, is_day = current.get("temperature_2m"), current.get("weather_code"), current.get("is_day")
        if type(temperature) not in (int, float) or type(code) is not int or is_day not in (0, 1):
            raise ProviderError("Réponse météo incomplète.")
        return Conditions(float(temperature), code, bool(is_day))

    def search_url(self, query: str) -> str:
        return f"{self.geocoding_endpoint}?" + urlencode(
            {"name": query.strip(), "count": MAX_RESULTS, "language": "fr", "format": "json"})

    def parse_search(self, data: object) -> list[City]:
        _raise_api_error(data)
        # Aucune ville trouvée : Open-Meteo renvoie un objet sans clé « results ».
        results = data.get("results", []) if isinstance(data, dict) else None
        if not isinstance(results, list):
            raise ProviderError("Réponse de recherche inattendue.")
        cities: list[City] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            name, lat, lon = item.get("name"), item.get("latitude"), item.get("longitude")
            if not isinstance(name, str) or type(lat) not in (int, float) or type(lon) not in (int, float):
                continue
            region = item.get("admin1") if isinstance(item.get("admin1"), str) else ""
            country = item.get("country") if isinstance(item.get("country"), str) else ""
            city = City(name[:80], region[:80], country[:60], float(lat), float(lon))
            if not any(c.label == city.label and c.same_place(city) for c in cities):
                cities.append(city)
        return cities


def _raise_api_error(data: object) -> None:
    if isinstance(data, dict) and data.get("error") is True:
        raise ProviderError(f"Le service météo a refusé la demande ({data.get('reason', 'raison inconnue')}).")

"""Module météo : fournisseur Open-Meteo, cache, service (sans aucun accès réseau réel)."""

import json
import unittest
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import support

from sigildesk.domain.weather import City, Conditions, ProviderError, describe, format_temperature
from sigildesk.infra.config_store import ConfigStore
from sigildesk.infra.open_meteo import OpenMeteo
from sigildesk.infra.paths import DEFAULT_CONFIG
from sigildesk.infra.weather_cache import WeatherCache

TOURS = City("Tours", "Centre-Val de Loire", "France", 47.39484, 0.70398)
PARIS_TZ = timezone(timedelta(hours=1))
CURRENT_OK = {"current": {"time": "2026-10-28T00:45", "interval": 900, "temperature_2m": 10.6, "weather_code": 1, "is_day": 0}}
SEARCH_OK = {"results": [
    {"name": "Tours", "latitude": 47.39484, "longitude": 0.70398, "country": "France", "admin1": "Centre-Val de Loire"},
    {"name": "Tours", "latitude": 50.03, "longitude": 1.5, "country": "France", "admin1": "Hauts-de-France"},
]}


class FakeHttp:
    """Répond depuis une file de réponses préparées ; garde la trace des adresses demandées."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.urls = []

    def get_json(self, url, callback):
        self.urls.append(url)
        data, error = self.answers.pop(0) if self.answers else (None, "hors-ligne")
        callback(data, error)


class Clock:
    def __init__(self):
        self.value = datetime(2026, 10, 28, 14, 5, tzinfo=PARIS_TZ)

    def __call__(self):
        return self.value


class DomainTests(unittest.TestCase):
    def test_codes(self):
        self.assertEqual(describe(0, True), ("Ensoleillé", "meteo-soleil"))
        self.assertEqual(describe(0, False), ("Ciel dégagé", "meteo-lune"))
        self.assertEqual(describe(2, False), ("Partiellement nuageux", "meteo-eclaircies-nuit"))
        self.assertEqual(describe(3, True)[1], "meteo-nuages")
        self.assertEqual(describe(45, True)[1], "meteo-brouillard")
        self.assertEqual(describe(63, True), ("Pluie", "meteo-pluie"))
        self.assertEqual(describe(73, False)[1], "meteo-neige")
        self.assertEqual(describe(95, True), ("Orage", "meteo-orage"))
        self.assertEqual(describe(1234, True)[0], "Conditions inconnues")

    def test_every_icon_exists(self):
        from sigildesk.infra.paths import ICONS_DIR

        for code in (0, 1, 2, 3, 45, 51, 61, 71, 80, 95):
            for day in (True, False):
                self.assertTrue((ICONS_DIR / f"{describe(code, day)[1]}.svg").is_file())
        self.assertTrue((ICONS_DIR / "meteo-indisponible.svg").is_file())

    def test_temperature_format(self):
        self.assertEqual(format_temperature(10.6), "11 °C")
        self.assertEqual(format_temperature(-0.3), "0 °C")
        self.assertEqual(format_temperature(-3.4), "−3 °C")


class OpenMeteoTests(unittest.TestCase):
    provider = OpenMeteo()

    def test_current_url_asks_only_three_fields(self):
        params = parse_qs(urlsplit(self.provider.current_url(TOURS)).query)
        self.assertEqual(params["current"], ["temperature_2m,weather_code,is_day"])
        self.assertEqual(params["latitude"], ["47.3948"])
        self.assertEqual(params["longitude"], ["0.7040"])
        self.assertNotIn("hourly", params)
        self.assertNotIn("daily", params)

    def test_parse_current(self):
        self.assertEqual(self.provider.parse_current(CURRENT_OK), Conditions(10.6, 1, False))
        for bad in ({}, {"current": {}}, {"current": {"temperature_2m": "10", "weather_code": 1, "is_day": 1}},
                    {"error": True, "reason": "Latitude must be in range"}, None, []):
            with self.subTest(bad=bad), self.assertRaises(ProviderError):
                self.provider.parse_current(bad)

    def test_search_url_is_encoded(self):
        params = parse_qs(urlsplit(self.provider.search_url("  Saint-Étienne & co ")).query)
        self.assertEqual(params["name"], ["Saint-Étienne & co"])
        self.assertEqual(params["language"], ["fr"])

    def test_parse_search(self):
        cities = self.provider.parse_search(SEARCH_OK)
        self.assertEqual([c.label for c in cities], ["Tours (Centre-Val de Loire, France)", "Tours (Hauts-de-France, France)"])
        # Ville inexistante : Open-Meteo renvoie un objet sans « results ».
        self.assertEqual(self.provider.parse_search({"generationtime_ms": 0.06}), [])
        self.assertEqual(self.provider.parse_search({"results": [{"name": 3}, "x"]}), [])
        with self.assertRaises(ProviderError):
            self.provider.parse_search({"error": True, "reason": "x"})


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.cache = WeatherCache(support.TempDir(self).path / "cache" / "meteo.json")
        self.when = datetime(2026, 10, 28, 9, 0, tzinfo=PARIS_TZ)

    def test_round_trip(self):
        self.cache.save(TOURS, "Open-Meteo", Conditions(10.6, 1, False), self.when)
        cached = self.cache.load(TOURS)
        self.assertEqual(cached.conditions, Conditions(10.6, 1, False))
        self.assertEqual(cached.fetched_at, self.when)

    def test_other_city_ignored(self):
        self.cache.save(TOURS, "Open-Meteo", Conditions(10.6, 1, False), self.when)
        self.assertIsNone(self.cache.load(City("Lille", "", "France", 50.63, 3.06)))

    def test_missing_or_corrupt_file(self):
        self.assertIsNone(self.cache.load(TOURS))
        self.cache.path.parent.mkdir(parents=True, exist_ok=True)
        for content in ("{pas du json", json.dumps({"version": 1}), json.dumps({"version": 99}),
                        json.dumps({"version": 1, "city": TOURS.to_dict(), "fetched_at": "2026-10-28T09:00:00",
                                    "conditions": {"temperature": 1, "code": 1, "is_day": True}})):
            with self.subTest(content=content[:30]):
                self.cache.path.write_text(content, encoding="utf-8")
                self.assertIsNone(self.cache.load(TOURS))


class ServiceTests(unittest.TestCase):
    def setUp(self):
        support.qt_app()
        self.clock = Clock()

    def make(self, http, city=TOURS, enabled=True, network=True):
        from sigildesk.ui.weather_service import WeatherService

        doc = support.default_document()
        doc["weather"] = {"enabled": enabled, "city": city.to_dict() if city else None}
        self.store, root = support.make_store(self, doc)
        self.cache = WeatherCache(root / "cache" / "meteo.json")
        return WeatherService(self.store, OpenMeteo(), self.cache, http, network=network, now=self.clock)

    def test_fetch_at_start_then_hourly(self):
        from sigildesk.ui.weather_service import REFRESH_MS

        http = FakeHttp((CURRENT_OK, None))
        service = self.make(http)
        service.start()
        self.assertEqual(len(http.urls), 1)
        self.assertEqual(service.property("state"), "ok")
        self.assertEqual(service.property("temperature"), "11 °C")
        self.assertEqual(service.property("condition"), "Plutôt dégagé")
        self.assertEqual(service.property("iconName"), "meteo-eclaircies-nuit")
        self.assertEqual(service.property("cityName"), "Tours")
        self.assertEqual(service.next_refresh_ms, REFRESH_MS)
        self.assertEqual(REFRESH_MS, 60 * 60 * 1000)
        self.assertEqual(self.cache.load(TOURS).conditions, Conditions(10.6, 1, False))

    def test_network_error_without_cache(self):
        from sigildesk.ui.weather_service import RETRY_MS

        service = self.make(FakeHttp((None, "hors-ligne")))
        service.start()
        self.assertEqual(service.property("state"), "unavailable")
        self.assertEqual(service.property("temperature"), "")
        self.assertEqual(service.next_refresh_ms, RETRY_MS)

    def test_network_error_shows_cached_data_with_time(self):
        http = FakeHttp((None, "hors-ligne"))
        service = self.make(http)
        self.cache.save(TOURS, "Open-Meteo", Conditions(4.2, 61, True), self.clock.value - timedelta(days=1, hours=3))
        service.reload_cache()  # comme au démarrage : le cache est lu avant la première requête
        service.start()
        self.assertEqual(service.property("state"), "stale")
        self.assertEqual(service.property("temperature"), "4 °C")
        self.assertEqual(service.property("condition"), "Pluie faible")
        self.assertEqual(service.property("updatedLabel"), "Mis à jour hier à 11:05")

    def test_service_error_payload(self):
        service = self.make(FakeHttp(({"error": True, "reason": "panne"}, None)))
        service.start()
        self.assertEqual(service.property("state"), "unavailable")

    def test_stale_after_ninety_minutes(self):
        service = self.make(FakeHttp((CURRENT_OK, None)))
        service.start()
        self.clock.value += timedelta(minutes=91)
        self.assertEqual(service.property("state"), "stale")
        self.assertEqual(service.property("updatedLabel"), "Mis à jour à 14:05")

    def test_recent_cache_counts_as_fresh(self):
        service = self.make(FakeHttp(), network=False)
        self.cache.save(TOURS, "Open-Meteo", Conditions(12.0, 0, True), self.clock.value - timedelta(minutes=20))
        service.reload_cache()
        service.start()
        self.assertEqual(service.property("state"), "ok")

    def test_disabled_makes_no_request(self):
        http = FakeHttp()
        service = self.make(http, enabled=False)
        service.start()
        service.refresh()
        self.assertEqual(http.urls, [])
        self.assertEqual(service.property("state"), "off")
        self.assertFalse(service.property("weatherEnabled"))

    def test_disabling_stops_refresh_and_persists(self):
        http = FakeHttp((CURRENT_OK, None))
        service = self.make(http)
        service.start()
        self.assertEqual(service.setEnabled(False), "")
        self.assertEqual(service.next_refresh_ms, 0)
        service.refresh()
        self.assertEqual(len(http.urls), 1)
        again = ConfigStore(self.store.path, DEFAULT_CONFIG)
        again.load()
        self.assertFalse(again.data["weather"]["enabled"])
        self.assertEqual(again.data["weather"]["city"]["name"], "Tours")

    def test_no_city(self):
        http = FakeHttp()
        service = self.make(http, city=None)
        service.start()
        self.assertEqual(service.property("state"), "no_city")
        self.assertEqual(http.urls, [])

    def test_no_network_mode_uses_cache_only(self):
        http = FakeHttp()
        service = self.make(http, network=False)
        service.start()
        self.assertEqual(http.urls, [])
        self.assertEqual(service.property("state"), "unavailable")

    def test_search_and_choose_city(self):
        http = FakeHttp((SEARCH_OK, None), (CURRENT_OK, None))
        service = self.make(http, city=None)
        service.search("Tours")
        results = service.property("searchResults")
        self.assertEqual([r["label"] for r in results][0], "Tours (Centre-Val de Loire, France)")
        self.assertEqual(service.chooseCity(0), "")
        self.assertEqual(service.property("state"), "ok")
        again = ConfigStore(self.store.path, DEFAULT_CONFIG)
        again.load()
        self.assertEqual(again.data["weather"]["city"]["region"], "Centre-Val de Loire")

    def test_unknown_city(self):
        service = self.make(FakeHttp(({"generationtime_ms": 0.07}, None)), city=None)
        service.search("Zzqxwvville")
        self.assertEqual(service.property("searchResults"), [])
        self.assertIn("Aucune ville trouvée", service.property("searchMessage"))
        self.assertNotEqual(service.chooseCity(0), "")

    def test_search_network_error(self):
        service = self.make(FakeHttp((None, "hors-ligne")), city=None)
        service.search("Tours")
        self.assertIn("pas de connexion", service.property("searchMessage"))
        self.assertFalse(service.property("searching"))

    def test_search_too_short(self):
        http = FakeHttp()
        service = self.make(http, city=None)
        service.search(" T ")
        self.assertEqual(http.urls, [])
        self.assertIn("deux lettres", service.property("searchMessage"))

    def test_late_answer_for_previous_city_is_ignored(self):
        from sigildesk.ui.weather_service import WeatherService

        pending = []

        class SlowHttp:
            def get_json(self, url, callback):
                pending.append(callback)

        doc = support.default_document()
        doc["weather"] = {"enabled": True, "city": TOURS.to_dict()}
        store, root = support.make_store(self, doc)
        service = WeatherService(store, OpenMeteo(), WeatherCache(root / "c.json"), SlowHttp(), now=self.clock)
        service.start()
        service.setEnabled(False)
        pending[0](CURRENT_OK, None)  # la réponse arrive après la désactivation
        self.assertEqual(service.property("state"), "off")
        self.assertEqual(service.property("temperature"), "")


if __name__ == "__main__":
    unittest.main()

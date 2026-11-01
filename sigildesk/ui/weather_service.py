"""Service météo pour le QML : relie fournisseur, cache et réglages.

Tout est asynchrone (`infra.http_client` sur la boucle d'événements) : aucun
fil ni processus supplémentaire, l'interface ne se bloque jamais.
Actualisation au démarrage puis toutes les 60 minutes ; après un échec, nouvel
essai au bout de 15 minutes. Désactivé, le service ne fait plus aucune requête.

États exposés (`state`) : « off », « no_city », « loading », « unavailable »,
« ok » (donnée de moins de 90 min) ou « stale » (plus ancienne, relue du cache).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from sigildesk.domain.settings import ConfigError
from sigildesk.domain.weather import City, ProviderError, WeatherProvider, describe, format_temperature, updated_label
from sigildesk.infra.config_store import ConfigStore
from sigildesk.infra.weather_cache import CachedWeather, WeatherCache

log = logging.getLogger(__name__)

REFRESH_MS = 60 * 60 * 1000
RETRY_MS = 15 * 60 * 1000
FRESH_FOR = timedelta(minutes=90)


def _now() -> datetime:
    return datetime.now().astimezone()


class WeatherService(QObject):
    changed = Signal()
    searchChanged = Signal()

    def __init__(
        self,
        store: ConfigStore,
        provider: WeatherProvider,
        cache: WeatherCache,
        http,
        network: bool = True,
        now: Callable[[], datetime] = _now,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._store = store
        self._provider = provider
        self._cache = cache
        self._http = http
        self._network = network
        self._now = now
        # La ville est relue du JSON une fois par changement, pas à chaque propriété lue par le QML.
        self._city: City | None = self._city_from_store()
        self._current: CachedWeather | None = self._cache.load(self._city) if self._city else None
        self._loading = False
        self._generation = 0  # numéro de la dernière demande : une réponse plus ancienne est ignorée
        self._search_results: list[City] = []
        self._search_message = ""
        self._searching = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.refresh)

    # --- État --------------------------------------------------------------------------

    def _city_from_store(self) -> City | None:
        data = self._store.data["weather"]["city"]
        return City.from_dict(data) if data else None

    @property
    def city(self) -> City | None:
        return self._city

    @property
    def enabled(self) -> bool:
        return self._store.data["weather"]["enabled"]

    @property
    def next_refresh_ms(self) -> int:
        return self._timer.interval() if self._timer.isActive() else 0

    def reload_cache(self) -> None:
        """Relit le cache pour la ville courante (comme au démarrage), sans requête réseau."""
        self._current = self._cache.load(self._city) if self._city else None

    def _state(self) -> str:
        if not self.enabled:
            return "off"
        if self._city is None:
            return "no_city"
        if self._current is None:
            return "loading" if self._loading else "unavailable"
        # Fraîcheur selon l'âge de la donnée, même relue du cache au démarrage.
        return "ok" if self._now() - self._current.fetched_at < FRESH_FOR else "stale"

    def _display(self) -> tuple[str, str]:
        if self._current is None:
            return "", "meteo-indisponible"
        return describe(self._current.conditions.code, self._current.conditions.is_day)

    state = Property(str, lambda self: self._state(), notify=changed)
    weatherEnabled = Property(bool, lambda self: self.enabled, notify=changed)
    temperature = Property(
        str, lambda self: format_temperature(self._current.conditions.temperature) if self._current else "",
        notify=changed)
    condition = Property(str, lambda self: self._display()[0], notify=changed)
    iconName = Property(str, lambda self: self._display()[1], notify=changed)
    cityName = Property(str, lambda self: self._city.name if self._city else "", notify=changed)
    cityLabel = Property(str, lambda self: self._city.label if self._city else "", notify=changed)
    updatedLabel = Property(
        str, lambda self: updated_label(self._current.fetched_at, self._now()) if self._current else "", notify=changed)
    attribution = Property(str, lambda self: self._provider.attribution, constant=True)
    attributionUrl = Property(str, lambda self: self._provider.attribution_url, constant=True)
    searching = Property(bool, lambda self: self._searching, notify=searchChanged)
    searchMessage = Property(str, lambda self: self._search_message, notify=searchChanged)
    searchResults = Property("QVariantList", lambda self: [
        {"index": i, "label": city.label} for i, city in enumerate(self._search_results)], notify=searchChanged)

    # --- Actualisation ------------------------------------------------------------------

    @Slot()
    def start(self) -> None:
        """Au démarrage : affiche le cache, puis va chercher des données fraîches."""
        self.changed.emit()
        self.refresh()

    @Slot()
    def refresh(self) -> None:
        self._timer.stop()
        city = self._city
        if not self.enabled or city is None or not self._network:
            return
        self._generation += 1
        generation = self._generation
        self._loading = True
        self.changed.emit()
        self._http.get_json(self._provider.current_url(city),
                            lambda data, error: self._on_current(generation, city, data, error))

    def _on_current(self, generation: int, city: City, data: object, error: str | None) -> None:
        if generation != self._generation:
            return  # réponse d'une demande périmée (ville changée ou météo coupée entre-temps)
        self._loading = False
        try:
            if error:
                raise ProviderError(error)
            conditions = self._provider.parse_current(data)
        except ProviderError as exc:
            log.info("météo non actualisée : %s", exc)
            self._schedule(RETRY_MS)
            self.changed.emit()
            return
        fetched_at = self._now()
        self._current = CachedWeather(conditions, fetched_at)
        self._cache.save(city, self._provider.name, conditions, fetched_at)
        self._schedule(REFRESH_MS)
        self.changed.emit()

    def _schedule(self, interval_ms: int) -> None:
        if self.enabled and self._city is not None and self._network:
            self._timer.start(interval_ms)

    # --- Réglages -----------------------------------------------------------------------

    def _save(self, enabled: bool, city: City | None) -> str:
        document = self._store.copy()
        document["weather"] = {"enabled": enabled, "city": city.to_dict() if city else None}
        try:
            self._store.replace(document)
        except (ConfigError, OSError) as exc:
            log.error("réglage météo non enregistré : %s", exc)
            return "Impossible d'enregistrer ce réglage."
        self._city = city
        return ""

    @Slot(bool, result=str)
    def setEnabled(self, enabled: bool) -> str:
        error = self._save(bool(enabled), self._city)
        if error:
            return error
        if enabled:
            self.start()
        else:
            self._timer.stop()
            self._generation += 1  # ignore une réponse encore en route
            self._loading = False
            self.changed.emit()
        return ""

    @Slot(str)
    def search(self, query: str) -> None:
        query = (query or "").strip()
        self._search_results = []
        if len(query) < 2:
            self._set_search("Tapez au moins deux lettres du nom de la ville.")
            return
        if len(query) > 80:
            self._set_search("Nom de ville trop long.")
            return
        if not self._network:
            self._set_search("Recherche indisponible hors connexion.")
            return
        self._searching = True
        self._set_search("Recherche…")
        self._http.get_json(self._provider.search_url(query), lambda data, error: self._on_search(query, data, error))

    def _on_search(self, query: str, data: object, error: str | None) -> None:
        self._searching = False
        if error == "hors-ligne":
            self._set_search("Recherche impossible : pas de connexion Internet.")
            return
        try:
            if error:
                raise ProviderError("Le service de recherche ne répond pas.")
            self._search_results = self._provider.parse_search(data)
        except ProviderError as exc:
            self._set_search(str(exc))
            return
        if not self._search_results:
            self._set_search(f"Aucune ville trouvée pour « {query} ». Vérifiez l'orthographe.")
        else:
            self._set_search("Choisissez votre ville dans la liste :")

    def _set_search(self, message: str) -> None:
        self._search_message = message
        self.searchChanged.emit()

    @Slot(int, result=str)
    def chooseCity(self, index: int) -> str:
        if not 0 <= index < len(self._search_results):
            return "Cette ville n'est plus dans la liste."
        city = self._search_results[index]
        error = self._save(self.enabled, city)
        if error:
            return error
        self._search_results = []
        self._set_search(f"Ville enregistrée : {city.label}.")
        self._current = self._cache.load(city)
        self.start()
        return ""

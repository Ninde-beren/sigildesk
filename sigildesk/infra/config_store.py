"""Le fichier de réglages : lecture tolérante, écriture atomique, validation à chaque passage.

Trois situations à la lecture :

- fichier absent → valeurs livrées (`config/default.json`) ;
- fichier illisible ou invalide → mis de côté sous `config.invalide-<date>.json`,
  valeurs livrées, et l'interface le signale ;
- fichier écrit par une version plus récente de SigilDesk → jamais écrasé : les
  réglages tiennent en mémoire pour la session (`read_only`).

Un fichier plus ancien est migré (`domain.settings.MIGRATIONS`) puis validé
comme un autre.
"""

from __future__ import annotations

import copy
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path

from sigildesk.domain.settings import SCHEMA_VERSION, ConfigError, migrate, validate
from sigildesk.infra.files import atomic_write_json

log = logging.getLogger(__name__)


def load_defaults(path: Path) -> dict:
    """Les valeurs livrées doivent être valides : sinon c'est un bug de paquet."""
    with path.open(encoding="utf-8") as handle:
        return validate(json.load(handle))


@dataclass(frozen=True)
class LoadReport:
    status: str  # "defaults", "loaded", "migrated", "recovered" ou "future"
    message: str = ""


class ConfigStore:
    """Détient la configuration courante ; toute écriture passe par `replace`.

    `data` est le document en vigueur, à lire seulement. Pour modifier : prendre
    `copy()`, changer la copie, puis `replace(copie)`, qui valide et enregistre
    d'un bloc, ou lève sans rien changer.
    """

    def __init__(self, path: Path, defaults_path: Path):
        self.path = path
        self._defaults = load_defaults(defaults_path)
        self._data = copy.deepcopy(self._defaults)
        self.read_only = False

    @property
    def defaults(self) -> dict:
        return copy.deepcopy(self._defaults)

    @property
    def data(self) -> dict:
        return self._data

    def copy(self) -> dict:
        return copy.deepcopy(self._data)

    def load(self) -> LoadReport:
        if not self.path.exists():
            self._data = copy.deepcopy(self._defaults)
            return LoadReport("defaults")
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            return self._recover(f"fichier illisible ({exc})")

        version = raw.get("schema_version") if isinstance(raw, dict) else None
        if type(version) is int and version > SCHEMA_VERSION:
            self.read_only = True
            self._data = copy.deepcopy(self._defaults)
            message = f"configuration en version {version}, plus récente que SigilDesk ; réglages non enregistrés"
            log.warning(message)
            return LoadReport("future", message)
        try:
            self._data = validate(migrate(raw))
        except ConfigError as exc:
            return self._recover(str(exc))
        if version != SCHEMA_VERSION:
            log.info("configuration migrée de la version %s à la version %s", version, SCHEMA_VERSION)
            return LoadReport("migrated")
        return LoadReport("loaded")

    def _recover(self, reason: str) -> LoadReport:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup = self.path.with_name(f"config.invalide-{stamp}.json")
        try:
            os.replace(self.path, backup)
            where = f" ; copie gardée dans {backup}"
        except OSError:
            where = ""
        self._data = copy.deepcopy(self._defaults)
        message = f"configuration invalide : {reason}{where}"
        log.warning(message)
        return LoadReport("recovered", message)

    def replace(self, document: dict) -> None:
        """Valide puis enregistre. Lève `ConfigError` ou `OSError` sans rien changer."""
        valid = validate(document)
        if not self.read_only:
            atomic_write_json(self.path, valid)
        self._data = valid

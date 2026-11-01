import copy
import json
import unittest

import support

from sigildesk.domain.settings import SCHEMA_VERSION, ConfigError, validate
from sigildesk.infra.config_store import ConfigStore
from sigildesk.infra.paths import DEFAULT_CONFIG


class ValidateTests(unittest.TestCase):
    def setUp(self):
        self.doc = support.default_document()

    def test_packaged_defaults_are_valid(self):
        valid = validate(self.doc)
        self.assertEqual(valid["schema_version"], SCHEMA_VERSION)
        self.assertEqual(set(valid["web"]), {"internet", "facebook", "mail", "youtube"})
        # La messagerie n'est pas présumée (pas de Gmail par défaut).
        self.assertEqual(valid["web"]["mail"], {"provider": "", "url": ""})

    def test_unknown_key_rejected(self):
        self.doc["commande"] = "rm -rf /"
        with self.assertRaisesRegex(ConfigError, "clé inconnue"):
            validate(self.doc)

    def test_missing_key_rejected(self):
        del self.doc["appearance"]["comfort"]
        with self.assertRaisesRegex(ConfigError, "clé manquante"):
            validate(self.doc)

    def test_types_are_strict(self):
        cases = [
            (("appearance", "comfort"), 1),
            (("appearance", "comfort"), "true"),
            (("schema_version",), "1"),
            (("browser",), "/usr/bin/evil"),
            (("window", "mode"), "kiosque"),
            (("folders", "photos"), "/etc"),
        ]
        for path, value in cases:
            doc = copy.deepcopy(self.doc)
            target = doc
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            with self.subTest(path=path, value=value), self.assertRaises(ConfigError):
                validate(doc)

    def test_web_urls_must_be_http(self):
        self.doc["web"]["youtube"] = "javascript:alert(1)"
        with self.assertRaises(ConfigError):
            validate(self.doc)

    def test_mail_provider_url_comes_from_catalog(self):
        self.doc["web"]["mail"] = {"provider": "orange", "url": "https://piege.example/"}
        self.assertEqual(validate(self.doc)["web"]["mail"]["url"], "https://messagerie.orange.fr/")

    def test_mail_custom_requires_valid_url(self):
        self.doc["web"]["mail"] = {"provider": "autre", "url": "webmail.exemple.fr"}
        self.assertEqual(validate(self.doc)["web"]["mail"]["url"], "https://webmail.exemple.fr/")
        self.doc["web"]["mail"] = {"provider": "autre", "url": "file:///home"}
        with self.assertRaises(ConfigError):
            validate(self.doc)

    def test_mail_url_must_be_empty_without_provider(self):
        self.doc["web"]["mail"] = {"provider": "", "url": "https://mail.exemple.fr/"}
        with self.assertRaises(ConfigError):
            validate(self.doc)

    def test_shortcut_validated(self):
        self.doc["maintenance"]["shortcut"] = "M"
        with self.assertRaises(ConfigError):
            validate(self.doc)

    def test_weather_city_validated(self):
        self.doc["weather"]["city"] = {"name": "Tours", "region": "", "country": "France", "latitude": 47.39, "longitude": 0.7}
        self.assertEqual(validate(self.doc)["weather"]["city"]["latitude"], 47.39)
        for field, bad in (("latitude", 91), ("longitude", "0.7"), ("latitude", True), ("name", "")):
            doc = copy.deepcopy(self.doc)
            doc["weather"]["city"][field] = bad
            with self.subTest(field=field, bad=bad), self.assertRaises(ConfigError):
                validate(doc)

    def test_wallpaper_id_cannot_be_a_path(self):
        self.doc["appearance"]["wallpaper"] = "../../etc/passwd"
        with self.assertRaises(ConfigError):
            validate(self.doc)


class StoreTests(unittest.TestCase):
    def test_missing_file_uses_defaults_without_writing(self):
        store, root = support.make_store(self)
        self.assertEqual(store.data, validate(support.default_document()))
        self.assertFalse(store.path.exists())

    def test_round_trip(self):
        store, _ = support.make_store(self)
        doc = store.copy()
        doc["user_name"] = "Marie"
        store.replace(doc)
        again = ConfigStore(store.path, DEFAULT_CONFIG)
        self.assertEqual(again.load().status, "loaded")
        self.assertEqual(again.data["user_name"], "Marie")

    def test_invalid_document_never_written(self):
        store, _ = support.make_store(self)
        doc = store.copy()
        doc["browser"] = "bash"
        with self.assertRaises(ConfigError):
            store.replace(doc)
        self.assertFalse(store.path.exists())
        self.assertEqual(store.data["browser"], "auto")

    def test_corrupt_file_is_set_aside(self):
        store, _ = support.make_store(self)
        store.path.parent.mkdir(parents=True, exist_ok=True)
        store.path.write_text("{pas du json", encoding="utf-8")
        report = store.load()
        self.assertEqual(report.status, "recovered")
        backups = list(store.path.parent.glob("config.invalide-*.json"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(encoding="utf-8"), "{pas du json")
        self.assertEqual(store.data["browser"], "auto")

    def test_version_1_is_migrated(self):
        doc = support.default_document()
        doc["schema_version"] = 1
        del doc["weather"]
        del doc["appearance"]["show_labels"]
        doc["user_name"] = "Marie"
        store, _ = support.make_store(self, doc)
        self.assertEqual(store.data["schema_version"], SCHEMA_VERSION)
        self.assertEqual(store.data["weather"], {"enabled": True, "city": None})
        self.assertTrue(store.data["appearance"]["show_labels"])
        self.assertEqual(store.data["user_name"], "Marie")
        again = ConfigStore(store.path, DEFAULT_CONFIG)
        self.assertEqual(again.load().status, "migrated")

    def test_future_version_is_never_overwritten(self):
        doc = support.default_document()
        doc["schema_version"] = SCHEMA_VERSION + 1
        store, _ = support.make_store(self, doc)
        self.assertTrue(store.read_only)
        before = store.path.read_text(encoding="utf-8")
        changed = store.copy()
        changed["user_name"] = "Paul"
        store.replace(changed)
        self.assertEqual(store.path.read_text(encoding="utf-8"), before)
        self.assertEqual(json.loads(before)["schema_version"], SCHEMA_VERSION + 1)


if __name__ == "__main__":
    unittest.main()

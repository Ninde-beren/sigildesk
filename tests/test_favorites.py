import unittest

import support

from sigildesk.infra.config_store import ConfigStore
from sigildesk.infra.paths import DEFAULT_CONFIG


class FavoritesTests(unittest.TestCase):
    def setUp(self):
        support.qt_app()
        from sigildesk.ui.favorites_model import FavoritesModel

        doc = support.default_document()
        doc["favorites"] = []
        self.store, _ = support.make_store(self, doc)
        self.model = FavoritesModel(self.store)

    def names(self):
        return [self.model.get(i)["name"] for i in range(self.model.rowCount())]

    def reloaded(self):
        from sigildesk.ui.favorites_model import FavoritesModel

        store = ConfigStore(self.store.path, DEFAULT_CONFIG)
        store.load()
        return FavoritesModel(store)

    def test_add_validates_and_normalizes(self):
        self.assertEqual(self.model.add("Météo", "meteofrance.com", "fav-meteo"), "")
        self.assertEqual(self.model.get(0), {"name": "Météo", "url": "https://meteofrance.com/", "icon": "fav-meteo"})

    def test_add_rejects_bad_input(self):
        self.assertIn("nom", self.model.add("  ", "exemple.fr", "fav-etoile"))
        self.assertIn("http", self.model.add("Piège", "javascript:alert(1)", "fav-etoile"))
        self.assertIn("http", self.model.add("Fichier", "file:///home", "fav-etoile"))
        self.assertNotEqual(self.model.add("x" * 40, "exemple.fr", "fav-etoile"), "")
        self.assertEqual(self.model.rowCount(), 0)

    def test_unknown_icon_falls_back(self):
        self.model.add("Site", "exemple.fr", "../../etc/passwd")
        self.assertEqual(self.model.get(0)["icon"], "fav-etoile")

    def test_limit_of_twelve(self):
        for n in range(12):
            self.assertEqual(self.model.add(f"Site {n}", f"site{n}.fr", "fav-etoile"), "")
        self.assertFalse(self.model.property("canAdd"))
        self.assertIn("12", self.model.add("Treizième", "treize.fr", "fav-etoile"))
        self.assertEqual(self.model.rowCount(), 12)

    def test_update(self):
        self.model.add("Ancien", "ancien.fr", "fav-etoile")
        self.assertEqual(self.model.update(0, "Nouveau", "https://nouveau.fr/x", "fav-banque"), "")
        self.assertEqual(self.reloaded().get(0), {"name": "Nouveau", "url": "https://nouveau.fr/x", "icon": "fav-banque"})
        self.assertNotEqual(self.model.update(0, "Nouveau", "ftp://x.fr", "fav-banque"), "")
        self.assertNotEqual(self.model.update(5, "Hors liste", "x.fr", "fav-banque"), "")

    def test_remove(self):
        for name in ("A", "B", "C"):
            self.model.add(name, f"{name.lower()}.fr", "fav-etoile")
        self.assertTrue(self.model.remove(1))
        self.assertEqual(self.names(), ["A", "C"])
        self.assertFalse(self.model.remove(9))
        self.assertEqual([self.reloaded().get(i)["name"] for i in range(2)], ["A", "C"])

    def test_reorder_persists(self):
        for name in ("A", "B", "C"):
            self.model.add(name, f"{name.lower()}.fr", "fav-etoile")
        self.assertTrue(self.model.move(2, -1))
        self.assertEqual(self.names(), ["A", "C", "B"])
        self.assertTrue(self.model.move(0, 1))
        self.assertEqual(self.names(), ["C", "A", "B"])
        self.assertFalse(self.model.move(0, -1))
        self.assertFalse(self.model.move(2, 1))
        self.assertFalse(self.model.move(1, 2))
        again = self.reloaded()
        self.assertEqual([again.get(i)["name"] for i in range(3)], ["C", "A", "B"])

    def test_top_four_follow_order(self):
        for name in ("A", "B", "C", "D", "E"):
            self.model.add(name, f"{name.lower()}.fr", "fav-etoile")
        top = self.model.property("top")
        self.assertEqual([t["name"] for t in top], ["A", "B", "C", "D"])
        self.assertEqual(top[0], {"index": 0, "name": "A", "iconName": "fav-etoile", "host": "a.fr"})
        changes = []
        self.model.topChanged.connect(lambda: changes.append(True))
        self.model.move(4, -1)  # E passe devant D
        self.assertEqual([t["name"] for t in self.model.property("top")], ["A", "B", "C", "E"])
        self.model.remove(0)
        self.assertEqual([t["name"] for t in self.model.property("top")], ["B", "C", "E", "D"])
        self.assertEqual(len(changes), 2)

    def test_check_for_live_validation(self):
        self.assertEqual(self.model.check("Météo", "meteofrance.com"), "")
        self.assertNotEqual(self.model.check("Météo", "meteo france"), "")

    def test_write_failure_keeps_list_unchanged(self):
        self.model.add("A", "a.fr", "fav-etoile")
        self.store.path.parent.chmod(0o500)
        self.addCleanup(self.store.path.parent.chmod, 0o700)
        self.assertNotEqual(self.model.add("B", "b.fr", "fav-etoile"), "")
        self.assertEqual(self.names(), ["A"])


if __name__ == "__main__":
    unittest.main()

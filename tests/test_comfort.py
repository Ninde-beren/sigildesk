import unittest

import support

from sigildesk.infra.config_store import ConfigStore
from sigildesk.infra.paths import DEFAULT_CONFIG


class ComfortTests(unittest.TestCase):
    def setUp(self):
        support.qt_app()

    def test_text_sizes(self):
        from sigildesk.ui.theme import COMFORT, STANDARD

        for name in ("fontSmall", "fontBody", "fontLabel"):
            with self.subTest(size=name):
                self.assertTrue(14 <= getattr(STANDARD, name) <= 16)
                self.assertTrue(18 <= getattr(COMFORT, name) <= 20)
        self.assertTrue(60 <= STANDARD.iconSize <= 64 and 60 <= COMFORT.iconSize <= 64)
        self.assertGreater(COMFORT.controlHeight, STANDARD.controlHeight)
        self.assertGreater(COMFORT.focusWidth, STANDARD.focusWidth)
        self.assertGreater(COMFORT.cardOpacity, STANDARD.cardOpacity)

    def test_theme_switch_is_immediate(self):
        from sigildesk.ui.theme import Theme

        theme = Theme()
        changes = []
        theme.changed.connect(lambda: changes.append(theme.property("fontBody")))
        theme.set_comfort(True)
        self.assertEqual(changes, [19])
        self.assertTrue(theme.property("comfort"))
        theme.set_comfort(True)
        self.assertEqual(len(changes), 1)

    def test_controller_persists_and_reverts(self):
        from sigildesk.domain.commands import CommandBuilder
        from sigildesk.infra.launcher import Launcher
        from sigildesk.infra.paths import UserPaths
        from sigildesk.ui.controller import AppController
        from sigildesk.ui.favorites_model import FavoritesModel
        from sigildesk.ui.theme import Theme

        store, root = support.make_store(self)
        theme = Theme(store.data["appearance"]["comfort"])
        controller = AppController(store, theme, FavoritesModel(store), Launcher(CommandBuilder(lambda n: None)),
                                   UserPaths.from_environment(root), None, lambda: None)
        self.assertEqual(controller.setComfort(True), "")
        self.assertTrue(theme.property("comfort"))
        again = ConfigStore(store.path, DEFAULT_CONFIG)
        again.load()
        self.assertTrue(again.data["appearance"]["comfort"])
        self.assertEqual(controller.setComfort(False), "")
        self.assertFalse(theme.property("comfort"))
        again.load()
        self.assertFalse(again.data["appearance"]["comfort"])

        # « Noms sous les icônes » : indépendant du mode confort, mémorisé.
        self.assertTrue(controller.property("showLabels"))
        self.assertEqual(controller.setShowLabels(False), "")
        self.assertFalse(controller.property("showLabels"))
        again.load()
        self.assertFalse(again.data["appearance"]["show_labels"])
        self.assertFalse(again.data["appearance"]["comfort"])


if __name__ == "__main__":
    unittest.main()

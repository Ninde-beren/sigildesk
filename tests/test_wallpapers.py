import hashlib
import unittest

import support

from sigildesk.infra.config_store import ConfigStore
from sigildesk.infra.paths import DEFAULT_CONFIG


def make_image(path, width, height, color, fmt, alpha=False):
    from PySide6.QtGui import QColor, QImage

    image = QImage(width, height, QImage.Format.Format_ARGB32 if alpha else QImage.Format.Format_RGB32)
    image.fill(QColor(color))
    assert image.save(str(path), fmt), f"écriture {fmt} impossible"
    return path


class ImportTests(unittest.TestCase):
    def setUp(self):
        support.qt_app()
        self.tmp = support.TempDir(self).path
        self.dest = self.tmp / "data" / "wallpapers"

    def test_jpeg_png_webp_imported_as_clean_copy(self):
        from sigildesk.infra.wallpaper_store import import_image

        for fmt, ext in (("JPEG", "jpg"), ("PNG", "png"), ("WEBP", "webp")):
            with self.subTest(fmt=fmt):
                source = make_image(self.tmp / f"cle-usb.{ext}", 1600, 900, "#20304A", fmt)
                before = hashlib.sha256(source.read_bytes()).hexdigest()
                wallpaper = import_image(source, self.dest)
                self.assertEqual(wallpaper.path.parent, self.dest)
                self.assertTrue(wallpaper.path.is_file())
                self.assertEqual(wallpaper.tone, "dark")
                # L'original n'est pas touché ; la copie survit à son retrait.
                self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)
                source.unlink()
                self.assertTrue(wallpaper.path.is_file())

    def test_light_image_gets_light_tone(self):
        from sigildesk.infra.wallpaper_store import import_image

        wallpaper = import_image(make_image(self.tmp / "clair.png", 800, 600, "#F4F1EA", "PNG"), self.dest)
        self.assertEqual(wallpaper.tone, "light")

    def test_large_image_is_downscaled(self):
        from PySide6.QtGui import QImageReader

        from sigildesk.infra.wallpaper_store import import_image

        wallpaper = import_image(make_image(self.tmp / "grand.jpg", 4000, 3000, "#6688AA", "JPEG"), self.dest)
        size = QImageReader(str(wallpaper.path)).size()
        self.assertLessEqual(size.width(), 2560)
        self.assertLessEqual(size.height(), 1440)

    def test_same_image_twice_reuses_copy(self):
        from sigildesk.infra.wallpaper_store import import_image

        source = make_image(self.tmp / "photo.png", 800, 600, "#AABBCC", "PNG")
        self.assertEqual(import_image(source, self.dest).path, import_image(source, self.dest).path)
        self.assertEqual(len(list(self.dest.iterdir())), 1)

    def test_invalid_files_refused(self):
        from sigildesk.infra.wallpaper_store import WallpaperError, import_image

        text = self.tmp / "faux.jpg"
        text.write_text("ceci n'est pas une image", encoding="utf-8")
        empty = self.tmp / "vide.png"
        empty.write_bytes(b"")
        truncated = self.tmp / "tronquee.jpg"
        truncated.write_bytes(make_image(self.tmp / "ok.jpg", 800, 600, "#123456", "JPEG").read_bytes()[:200])
        tiny = make_image(self.tmp / "mini.png", 100, 80, "#FFFFFF", "PNG")
        for bad in (text, empty, truncated, tiny, self.tmp / "absente.png"):
            with self.subTest(bad=bad.name), self.assertRaises(WallpaperError):
                import_image(bad, self.dest)
        self.assertEqual(list(self.dest.glob("perso-*")) if self.dest.exists() else [], [])

    def test_bmp_refused_even_if_renamed(self):
        from sigildesk.infra.wallpaper_store import WallpaperError, import_image

        bmp = make_image(self.tmp / "image.bmp", 800, 600, "#ABCDEF", "BMP")
        renamed = bmp.rename(self.tmp / "image.png")
        with self.assertRaises(WallpaperError):
            import_image(renamed, self.dest)


class ModelTests(unittest.TestCase):
    def setUp(self):
        support.qt_app()
        self.store, root = support.make_store(self)
        self.dest = root / "data" / "wallpapers"
        self.root = root

    def model(self, store=None):
        from sigildesk.ui.wallpaper_model import WallpaperModel

        return WallpaperModel(store or self.store, self.dest)

    def test_builtin_default(self):
        model = self.model()
        self.assertEqual(model.property("currentId"), "aube")
        self.assertTrue(model.property("source").endswith("aube-solaire.jpg"))
        self.assertEqual(model.property("tone"), "light")

    def test_builtin_tones_match_images(self):
        from PySide6.QtGui import QImage

        from sigildesk.infra.wallpaper_store import BUILTINS, analyze_tone

        for wallpaper in BUILTINS:
            if wallpaper.path:
                with self.subTest(wallpaper=wallpaper.id):
                    self.assertEqual(analyze_tone(QImage(str(wallpaper.path))), wallpaper.tone)

    def test_preview_cancel_apply_persist(self):
        model = self.model()
        model.preview("orbite")
        self.assertTrue(model.property("previewing"))
        self.assertEqual(model.property("tone"), "dark")
        model.cancel()
        self.assertEqual(model.property("currentId"), "aube")
        self.assertEqual(self.store.data["appearance"]["wallpaper"], "aube")
        model.preview("blueprint")
        self.assertTrue(model.apply())
        again = ConfigStore(self.store.path, DEFAULT_CONFIG)
        again.load()
        self.assertEqual(self.model(again).property("currentId"), "blueprint")

    def test_import_preview_then_reset(self):
        model = self.model()
        image = make_image(self.root / "vacances.jpg", 1200, 800, "#336699", "JPEG")
        self.assertEqual(model.importFile(image.as_uri()), "")
        imported = model.property("selectedId")
        self.assertTrue(imported.startswith("perso-"))
        self.assertTrue(model.property("selectedIsImported"))
        self.assertTrue(model.apply())
        self.assertEqual(self.store.data["appearance"]["wallpaper"], imported)
        self.assertTrue(model.reset())
        self.assertEqual(self.store.data["appearance"]["wallpaper"], "aube")

    def test_import_error_message(self):
        model = self.model()
        self.assertIn("introuvable", model.importFile((self.root / "absente.png").as_uri()))
        self.assertNotEqual(model.importFile("https://exemple.fr/image.png"), "")

    def test_missing_copy_falls_back_to_default(self):
        model = self.model()
        image = make_image(self.root / "photo.png", 1200, 800, "#336699", "PNG")
        model.importFile(image.as_uri())
        model.apply()
        imported_id = self.store.data["appearance"]["wallpaper"]
        for path in self.dest.iterdir():
            path.unlink()
        again = self.model()
        self.assertNotEqual(imported_id, "aube")
        self.assertEqual(again.property("currentId"), "aube")

    def test_remove_imported_never_touches_builtin(self):
        model = self.model()
        self.assertFalse(model.removeImported("aube"))
        image = make_image(self.root / "photo.png", 1200, 800, "#336699", "PNG")
        model.importFile(image.as_uri())
        model.apply()
        imported_id = model.property("currentId")
        self.assertTrue(model.removeImported(imported_id))
        self.assertEqual(model.property("currentId"), "aube")
        self.assertTrue(image.is_file())  # l'original reste en place


if __name__ == "__main__":
    unittest.main()

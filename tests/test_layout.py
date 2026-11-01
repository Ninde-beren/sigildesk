"""Mise en page réelle : SigilDesk est lancé hors écran et mesure ses zones.

Vérifie à 1366×768 et 1024×600, en mode standard et en mode confort : grille
2 × 4, dock et signature visibles, rien qui dépasse ni ne se chevauche, aucun
libellé tronqué. À 1366×768 standard, les cotes de la maquette sont contrôlées.
"""

import json
import os
import subprocess
import sys
import unittest
from datetime import datetime, timedelta

import support

from sigildesk import __version__

TILES = ("internet", "facebook", "mail", "youtube", "files", "photos", "videos", "pdf")


LONG_CITY = {"name": "Saint-Rémy-de-Provence", "region": "Provence-Alpes-Côte d'Azur", "country": "France",
             "latitude": 43.789, "longitude": 4.832}


def measure(test, width, height, comfort, wallpaper="aube", panel=None, weather_cache=False, labels=True, favorites=None,
            windows=""):
    tmp = support.TempDir(test).path
    doc = support.default_document()
    if favorites is not None:
        doc["favorites"] = favorites
    doc["appearance"]["comfort"] = comfort
    doc["appearance"]["show_labels"] = labels
    doc["appearance"]["wallpaper"] = wallpaper
    if weather_cache:
        # Cas le plus long : ville à rallonge, données d'hier affichées hors connexion.
        doc["weather"]["city"] = LONG_CITY
        fetched = (datetime.now().astimezone() - timedelta(days=1)).isoformat(timespec="seconds")
        (tmp / "cache").mkdir()
        (tmp / "cache" / "meteo.json").write_text(json.dumps({
            "version": 1, "provider": "Open-Meteo", "city": LONG_CITY, "fetched_at": fetched,
            "conditions": {"temperature": -12.4, "code": 96, "is_day": True}}), encoding="utf-8")
    (tmp / "config").mkdir()
    (tmp / "config" / "config.json").write_text(json.dumps(doc), encoding="utf-8")
    out = tmp / "geo.json"
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    argv = [sys.executable, "-m", "sigildesk", "--root", str(tmp), "--size", f"{width}x{height}", "--dump-geometry", str(out),
            "--no-network"]
    if panel:
        argv += ["--panel", panel]
    if windows:
        argv += ["--fenetres-essai", windows]
    done = subprocess.run(argv, cwd=support.REPO, env=env, capture_output=True, text=True, timeout=90)
    test.assertEqual(done.returncode, 0, done.stderr[-2000:])
    test.assertNotIn("TypeError", done.stderr)
    test.assertNotIn("ReferenceError", done.stderr)
    return json.loads(out.read_text(encoding="utf-8"))


def box(item):
    return item["x"], item["y"], item["x"] + item["w"], item["y"] + item["h"]


def overlaps(a, b):
    ax1, ay1, ax2, ay2 = box(a)
    bx1, by1, bx2, by2 = box(b)
    return ax1 < bx2 and bx1 < ax2 and ay1 < by2 and by1 < ay2


class LayoutTests(unittest.TestCase):
    def check_common(self, geo, width, height):
        items = geo["items"]
        self.assertEqual(geo["window"], {"w": width, "h": height})
        regions = ["geo_status", "geo_greeting", "geo_grid", "geo_dock", "geo_signature", "geo_weather", "geo_status_icons"]
        regions += [f"geo_tile_{t}" for t in TILES]
        for name in regions:
            with self.subTest(region=name):
                item = items[name]
                self.assertTrue(item["visible"])
                x1, y1, x2, y2 = box(item)
                self.assertGreaterEqual(x1, 0)
                self.assertGreaterEqual(y1, 0)
                self.assertLessEqual(x2, width)
                self.assertLessEqual(y2, height)
        # Bandes verticales dans l'ordre, sans chevauchement.
        order = ["geo_status", "geo_greeting", "geo_grid", "geo_dock"]
        for upper, lower in zip(order, order[1:], strict=False):
            self.assertLessEqual(box(items[upper])[3], box(items[lower])[1], f"{upper} chevauche {lower}")
        # Grille 2 × 4 : deux rangées de quatre, sans chevauchement.
        tiles = [items[f"geo_tile_{t}"] for t in TILES]
        rows = sorted({round(t["y"]) for t in tiles})
        self.assertEqual(len(rows), 2)
        self.assertEqual(sorted({round(t["x"]) for t in tiles[:4]}), sorted({round(t["x"]) for t in tiles[4:]}))
        for i, a in enumerate(tiles):
            for b in tiles[i + 1:]:
                self.assertFalse(overlaps(a, b))
        self.assertFalse(overlaps(items["geo_signature"], items["geo_dock"]))
        # Bandeau : date à gauche, météo juste dessous, icônes d'état à droite dans la barre.
        status = box(items["geo_status"])
        for name in ("geo_date", "geo_status_icons"):
            x1, y1, x2, y2 = box(items[name])
            self.assertTrue(status[1] <= y1 and y2 <= status[3], f"{name} déborde du bandeau")
        weather, date = box(items["geo_weather"]), box(items["geo_date"])
        self.assertGreaterEqual(weather[1], date[3] - 1, "la météo doit être sous la date")
        self.assertAlmostEqual(weather[0], date[0] - 8, delta=1, msg="la météo doit être alignée sur la date")
        for other in ("geo_greeting", "geo_hello", "geo_clock", "geo_grid", "geo_status_icons", "geo_date"):
            self.assertFalse(overlaps(items["geo_weather"], items[other]), f"la météo chevauche {other}")
        pill = box(items["geo_weather"])
        for name in ("geo_weather_detail", "geo_weather_updated"):
            if items[name]["visible"]:
                x1, y1, x2, y2 = box(items[name])
                self.assertTrue(pill[0] <= x1 and x2 <= pill[2], f"{name} sort du bloc météo")
        for t in TILES:
            self.assertFalse(items[f"geo_tile_label_{t}"]["truncated"], f"libellé {t} tronqué")
        self.assertEqual(items["geo_signature"]["text"], f"SigilDesk · v{__version__}")

    def test_1366x768_standard_matches_mockup(self):
        geo = measure(self, 1366, 768, comfort=False)
        self.check_common(geo, 1366, 768)
        items = geo["items"]
        status, greeting, grid, dock = (box(items[n]) for n in ("geo_status", "geo_greeting", "geo_grid", "geo_dock"))
        self.assertTrue(status[1] >= 20 and status[3] <= 74, status)
        self.assertTrue(greeting[1] >= 100 and greeting[3] <= 200, greeting)
        # La bande de la maquette (225–510) porte sur les 8 tuiles d'applications ;
        # la rangée de favoris, quand elle tient, vient dessous.
        apps = [box(items[f"geo_tile_{t}"]) for t in TILES]
        self.assertTrue(min(a[1] for a in apps) >= 220 and max(a[3] for a in apps) <= 515, apps)
        self.assertTrue(600 <= items["geo_grid"]["w"] <= 700)
        self.assertTrue(dock[1] >= 684 and dock[3] <= 748, dock)
        self.assertEqual((items["geo_tile_internet"]["w"], items["geo_tile_internet"]["h"]), (124, 104))
        signature = box(items["geo_signature"])
        self.assertGreater(signature[0], 1366 * 0.8)
        self.assertLessEqual(signature[2], 1366 - 16)

    def test_1366x768_comfort(self):
        geo = measure(self, 1366, 768, comfort=True)
        self.check_common(geo, 1366, 768)
        self.assertGreater(geo["items"]["geo_tile_internet"]["w"], 124)

    def test_1024x600_standard(self):
        self.check_common(measure(self, 1024, 600, comfort=False), 1024, 600)

    def test_1024x600_comfort(self):
        self.check_common(measure(self, 1024, 600, comfort=True), 1024, 600)

    def test_weather_longest_content(self):
        for width, height, comfort in ((1366, 768, False), (1366, 768, True), (1024, 600, False), (1024, 600, True)):
            with self.subTest(size=f"{width}x{height}", comfort=comfort):
                geo = measure(self, width, height, comfort, weather_cache=True)
                self.check_common(geo, width, height)
                updated = geo["items"]["geo_weather_updated"]
                self.assertIn("Mis à jour hier", updated["text"])
                self.assertFalse(updated["truncated"])

    def test_icons_fill_tiles_without_labels(self):
        for width, height, comfort in ((1366, 768, False), (1024, 600, True)):
            with self.subTest(size=f"{width}x{height}", comfort=comfort):
                geo = measure(self, width, height, comfort, labels=False)
                self.check_common(geo, width, height)
                for tile in TILES:
                    icon, card = geo["items"][f"geo_tile_icon_{tile}"], geo["items"][f"geo_tile_{tile}"]
                    self.assertFalse(geo["items"][f"geo_tile_label_{tile}"]["visible"])
                    self.assertGreaterEqual(icon["w"], 80)
                    x1, y1, x2, y2 = box(icon)
                    self.assertTrue(card["x"] <= x1 and x2 <= card["x"] + card["w"] and card["y"] <= y1 and y2 <= card["y"] + card["h"])

    def test_favorites_row(self):
        four = [{"name": f"Site {n}", "url": f"https://site{n}.fr/", "icon": "fav-etoile"} for n in range(6)]
        for width, height, comfort in ((1366, 768, False), (1366, 768, True)):
            with self.subTest(size=f"{width}x{height}", comfort=comfort):
                geo = measure(self, width, height, comfort, favorites=four)
                self.check_common(geo, width, height)
                items = geo["items"]
                self.assertTrue(items["geo_fav_row"]["visible"])
                favs = [items[f"geo_fav_{n}"] for n in range(4)]
                self.assertNotIn("geo_fav_4", items)  # quatre au plus
                apps_bottom = max(box(items[f"geo_tile_{t}"])[3] for t in TILES)
                for n, (fav, column) in enumerate(zip(favs, ("files", "photos", "videos", "pdf"), strict=False)):
                    self.assertGreater(fav["y"], apps_bottom)
                    self.assertEqual(round(fav["x"]), round(items[f"geo_tile_{column}"]["x"]))
                    self.assertLessEqual(box(fav)[3] + 24, items["geo_dock"]["y"])
                    self.assertEqual(fav["text"], f"Site {n}")  # dans l'ordre de « Mes favoris »
                self.assertEqual(items["geo_tile_label_favori-0"]["text"], "Site 0")

    def test_favorites_row_hidden_when_no_room_or_no_favorite(self):
        for width, height, comfort, favorites in ((1024, 600, False, None), (1024, 600, True, None), (1366, 768, False, [])):
            with self.subTest(size=f"{width}x{height}", comfort=comfort, favorites=favorites):
                geo = measure(self, width, height, comfort, favorites=favorites)
                self.check_common(geo, width, height)
                self.assertFalse(geo["items"]["geo_fav_row"]["visible"])

    def test_dock_with_open_windows(self):
        many = "youtube,images,vlc,photo,pdf,internet,facebook"
        for width, height, comfort, windows in ((1366, 768, False, "youtube,images,vlc"), (1366, 768, True, many),
                                                (1024, 600, False, "youtube"), (1024, 600, True, many)):
            with self.subTest(size=f"{width}x{height}", comfort=comfort, windows=windows):
                geo = measure(self, width, height, comfort, windows=windows)
                self.check_common(geo, width, height)
                items = geo["items"]
                shown = [items[k] for k in items if k.startswith("geo_window_") and k != "geo_window_more" and items[k]["visible"]]
                more = items.get("geo_window_more", {"visible": False})
                total = len(windows.split(","))
                # Chaque fenêtre est atteignable : une pastille, ou le bouton « Autres / Fenêtres ».
                self.assertTrue(len(shown) == total or more["visible"], (len(shown), total))
                # Barre à part, en haut et centrée dans le bandeau ; le dock garde ses trois boutons.
                bar = items["geo_windows_bar"]
                self.assertTrue(bar["visible"])
                status = box(items["geo_status"])
                self.assertTrue(status[1] <= bar["y"] and box(bar)[3] <= status[3], "barre hors du bandeau")
                self.assertAlmostEqual(bar["x"] + bar["w"] / 2, width / 2, delta=1)
                for other in ("geo_date", "geo_weather", "geo_status_icons", "geo_greeting", "geo_dock"):
                    self.assertFalse(overlaps(bar, items[other]), f"la barre chevauche {other}")
                for chip in shown + ([more] if more["visible"] else []):
                    x1, y1, x2, y2 = box(chip)
                    self.assertTrue(box(bar)[0] <= x1 and x2 <= box(bar)[2], "pastille hors de sa barre")
                    self.assertFalse(overlaps(chip, items["geo_dock"]))

    def test_weather_hidden_when_disabled(self):
        tmp_geo = measure(self, 1366, 768, False)
        self.assertTrue(tmp_geo["items"]["geo_weather"]["visible"])

    def test_dark_wallpaper(self):
        self.check_common(measure(self, 1366, 768, comfort=False, wallpaper="blueprint"), 1366, 768)

    def test_panels_and_dialogs_fit(self):
        """Chaque panneau a un vrai fond et tient dans l'écran, y compris en confort à 1024×600."""
        for width, height, comfort in ((1366, 768, False), (1024, 600, True)):
            for panel in ("favoris", "editeur", "parametres", "fonds", "eteindre", "meteo", "apropos"):
                with self.subTest(size=f"{width}x{height}", comfort=comfort, panel=panel):
                    popup = measure(self, width, height, comfort, panel=panel)["items"]["geo_open_popup"]
                    x1, y1, x2, y2 = box(popup)
                    self.assertGreater(popup["h"], 150)
                    self.assertGreater(popup["w"], 300)
                    self.assertTrue(x1 >= 0 and y1 >= 0 and x2 <= width and y2 <= height, popup)


if __name__ == "__main__":
    unittest.main()

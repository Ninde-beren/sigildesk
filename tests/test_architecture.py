"""Les couches ne se croisent que dans un sens : domain ← infra ← ui ← app.

Lu dans le code source, sans importer les modules : un import interdit est une
erreur de conception, pas d'exécution.
"""

import ast
import unittest
from pathlib import Path

import support

PACKAGE = support.REPO / "sigildesk"


def imports_of(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def modules(layer: str) -> list[Path]:
    return sorted((PACKAGE / layer).glob("*.py"))


class LayerTests(unittest.TestCase):
    def assert_no_import(self, path: Path, forbidden: tuple[str, ...]):
        bad = sorted(name for name in imports_of(path) if name.startswith(forbidden))
        self.assertEqual(bad, [], f"{path.relative_to(PACKAGE)} importe {bad}")

    def test_domain_is_pure(self):
        for path in modules("domain"):
            with self.subTest(module=path.name):
                self.assert_no_import(path, ("PySide6", "sigildesk.infra", "sigildesk.ui", "sigildesk.app",
                                             "subprocess", "urllib.request", "socket"))

    def test_infra_does_not_know_ui(self):
        for path in modules("infra"):
            with self.subTest(module=path.name):
                self.assert_no_import(path, ("sigildesk.ui", "sigildesk.app", "sigildesk.devtools"))

    def test_ui_is_only_reached_from_app(self):
        for path in modules("ui"):
            with self.subTest(module=path.name):
                self.assert_no_import(path, ("sigildesk.app", "sigildesk.devtools", "sigildesk.cli"))

    def test_every_layer_has_a_docstring(self):
        for layer in ("domain", "infra", "ui"):
            for path in modules(layer):
                with self.subTest(module=f"{layer}/{path.name}"):
                    tree = ast.parse(path.read_text(encoding="utf-8"))
                    self.assertTrue(path.name == "__init__.py" or ast.get_docstring(tree), "module sans docstring")


if __name__ == "__main__":
    unittest.main()

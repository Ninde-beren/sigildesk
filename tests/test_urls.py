import unittest

import support  # noqa: F401  (chemin du dépôt)

from sigildesk.domain.urls import UrlError, display_host, is_web_url, normalize_web_url


class NormalizeTests(unittest.TestCase):
    def test_adds_https_and_trailing_slash(self):
        self.assertEqual(normalize_web_url("meteofrance.com"), "https://meteofrance.com/")
        self.assertEqual(normalize_web_url("  www.Exemple.FR/page?x=1  "), "https://www.exemple.fr/page?x=1")

    def test_keeps_http_and_port(self):
        self.assertEqual(normalize_web_url("http://exemple.fr:8080/a"), "http://exemple.fr:8080/a")
        self.assertEqual(normalize_web_url("exemple.fr:8443"), "https://exemple.fr:8443/")

    def test_accepts_idn_and_ip(self):
        self.assertEqual(normalize_web_url("https://café.fr/"), "https://café.fr/")
        self.assertEqual(normalize_web_url("http://192.168.1.10/"), "http://192.168.1.10/")

    def test_rejects_other_schemes(self):
        for bad in ("javascript:alert(1)", "file:///etc/passwd", "data:text/html,x", "mailto:a@b.fr",
                    "ftp://exemple.fr/", "chrome://settings", "about:blank", "-https://exemple.fr"):
            with self.subTest(bad=bad), self.assertRaises(UrlError):
                normalize_web_url(bad)

    def test_rejects_malformed(self):
        for bad in ("", "   ", "https://", "exemple", "https://exe mple.fr", "https://exemple.fr/\x00",
                    "//exemple.fr", "https://user:pass@exemple.fr/", "https://exemple.fr:99999/",
                    "https://-exemple.fr/", "https://exemple.f_r/", "x" * 3000):
            with self.subTest(bad=bad), self.assertRaises(UrlError):
                normalize_web_url(bad)

    def test_result_never_looks_like_an_option(self):
        for url in ("exemple.fr", "http://exemple.fr", "https://a.b.c.fr/-x"):
            self.assertTrue(normalize_web_url(url).startswith(("http://", "https://")))

    def test_helpers(self):
        self.assertTrue(is_web_url("lemonde.fr"))
        self.assertFalse(is_web_url("javascript:void(0)"))
        self.assertEqual(display_host("https://www.meteofrance.com/x"), "meteofrance.com")


if __name__ == "__main__":
    unittest.main()

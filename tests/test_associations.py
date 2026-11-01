import unittest

import support  # noqa: F401

from sigildesk.infra.xdg import CHECKS, check_associations, classify


class AssociationTests(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(classify("vlc.desktop", ("vlc", "mpv")), "ok")
        self.assertEqual(classify("org.videolan.vlc.desktop", ("vlc", "org.videolan.vlc")), "ok")
        self.assertEqual(classify("qpdfview-qt6.desktop", ("qpdfview",)), "ok")
        self.assertEqual(classify("org.gnome.Totem.desktop", ("vlc", "mpv")), "autre")
        self.assertEqual(classify("", ("vlc",)), "aucune")

    def test_queries_each_mime_with_separate_arguments(self):
        seen = []
        answers = {"video/mp4": "mpv.desktop\n", "application/pdf": "org.gnome.Evince.desktop\n", "image/jpeg": "lximage-qt.desktop\n"}

        def runner(argv):
            seen.append(argv)
            return answers.get(argv[-1], "")

        reports = {r.mime: r for r in check_associations("/usr/bin/xdg-mime", runner)}
        self.assertEqual(seen[0], ["/usr/bin/xdg-mime", "query", "default", CHECKS[0][0]])
        self.assertEqual(len(seen), len(CHECKS))
        self.assertEqual(reports["video/mp4"].status, "ok")
        self.assertEqual(reports["image/jpeg"].status, "ok")
        self.assertEqual(reports["application/pdf"].status, "autre")
        self.assertEqual(reports["application/pdf"].fix_command, "xdg-mime default qpdfview.desktop application/pdf")
        self.assertEqual(reports["image/webp"].status, "aucune")

    def test_without_xdg_mime(self):
        reports = check_associations(None, lambda argv: self.fail("ne doit rien lancer"))
        self.assertTrue(all(r.status == "aucune" for r in reports))


if __name__ == "__main__":
    unittest.main()

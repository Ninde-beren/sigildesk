import unittest

import support  # noqa: F401

from sigildesk.infra.video_decoding import INSTALL_HINT, check_hardware_decoding, parse_vainfo

# Sortie réelle du pilote i965 sur une puce Cherryview/Braswell (celle du Celeron N3060).
VAINFO = """libva info: VA-API version 1.22.0
libva info: Trying to open /usr/lib/x86_64-linux-gnu/dri/i965_drv_video.so
vainfo: VA-API version: 1.22 (libva 2.22.0)
vainfo: Driver version: Intel i965 driver for Intel(R) Cherryview/Braswell - 2.4.1
vainfo: Supported profile and entrypoints
      VAProfileMPEG2Simple            :\tVAEntrypointVLD
      VAProfileH264ConstrainedBaseline:\tVAEntrypointVLD
      VAProfileH264Main               :\tVAEntrypointVLD
      VAProfileH264Main               :\tVAEntrypointEncSlice
      VAProfileH264High               :\tVAEntrypointVLD
      VAProfileHEVCMain               :\tVAEntrypointVLD
      VAProfileJPEGBaseline           :\tVAEntrypointVLD
      VAProfileVP8Version0_3          :\tVAEntrypointVLD
      VAProfileNone                   :\tVAEntrypointVideoProc
"""


class VideoDecodingTests(unittest.TestCase):
    def test_parse_lists_decodable_codecs_once_in_display_order(self):
        codecs, driver = parse_vainfo(VAINFO)
        self.assertEqual(codecs, ("H.264", "HEVC", "VP8", "MPEG-2", "JPEG"))
        self.assertEqual(driver, "Intel i965 driver for Intel(R) Cherryview/Braswell - 2.4.1")

    def test_encode_only_profiles_do_not_count(self):
        self.assertEqual(parse_vainfo("      VAProfileH264Main : VAEntrypointEncSlice\n"), ((), ""))

    def test_report_with_driver(self):
        seen = []
        report = check_hardware_decoding("/usr/bin/vainfo", lambda argv: seen.append(argv) or VAINFO)
        self.assertEqual(seen, [["/usr/bin/vainfo"]])
        self.assertEqual(report.status, "ok")
        self.assertEqual(report.label,
                         "H.264, HEVC, VP8, MPEG-2, JPEG (Intel i965 driver for Intel(R) Cherryview/Braswell - 2.4.1)")
        self.assertEqual(report.hint, "")
        self.assertEqual(report.as_dict()["codecs"], ["H.264", "HEVC", "VP8", "MPEG-2", "JPEG"])

    def test_report_without_driver(self):
        # vainfo présent mais aucun pilote : échec (None) ou sortie sans profil.
        for output in (None, "libva error: vaGetDriverNames() failed\n"):
            with self.subTest(output=output):
                report = check_hardware_decoding("/usr/bin/vainfo", lambda argv, out=output: out)
                self.assertEqual((report.status, report.label, report.hint), ("aucun", "indisponible", INSTALL_HINT))

    def test_report_without_vainfo(self):
        report = check_hardware_decoding(None, lambda argv: self.fail("ne doit rien lancer"))
        self.assertEqual((report.status, report.label), ("absent", "non vérifiable"))
        self.assertIn("vainfo", report.hint)


if __name__ == "__main__":
    unittest.main()

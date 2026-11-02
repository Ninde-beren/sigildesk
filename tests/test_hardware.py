import os
import tempfile
import unittest
from pathlib import Path

import support  # noqa: F401

from sigildesk.infra import hardware
from sigildesk.infra.hardware import (
    STATUSES,
    check_additional_drivers,
    check_audio,
    check_firmware,
    check_opengl,
    check_pci,
    check_usb,
    collect_hardware_report,
    parse_asound_cards,
    parse_firmware_failures,
    parse_glxinfo,
    parse_lspci,
    parse_ubuntu_drivers,
    parse_wpctl_sink,
)

# Sorties réelles, raccourcies, d'une machine Lubuntu : la puce Intel de l'ASUS pour lspci.
LSPCI = (
    "Slot:\t00:00.0\nClass:\tHost bridge\nVendor:\tIntel Corporation\n"
    "Device:\tAtom/Celeron/Pentium Processor x5-E8000/J3xxx/N3xxx Series SoC Transaction Register\n\n"
    "Slot:\t00:02.0\nClass:\tVGA compatible controller\nVendor:\tIntel Corporation\n"
    "Device:\tAtom/Celeron/Pentium Processor x5-E8000/J3xxx/N3xxx Integrated Graphics Controller\n"
    "SVendor:\tASUSTeK Computer Inc.\nSDevice:\tDevice 1b6d\nRev:\t35\nProgIf:\t00\nDriver:\ti915\nModule:\ti915\n\n"
    "Slot:\t00:1b.0\nClass:\tAudio device\nVendor:\tIntel Corporation\n"
    "Device:\tAtom/Celeron/Pentium Processor x5-E8000/J3xxx/N3xxx Series High Definition Audio Controller\n"
    "Driver:\tsnd_hda_intel\nModule:\tsnd_hda_intel\nModule:\tsnd_soc_avs\n\n"
    "Slot:\t01:00.0\nClass:\tNetwork controller\nVendor:\tRealtek Semiconductor Co., Ltd.\n"
    "Device:\tRTL8723BE PCIe Wireless Network Adapter\nModule:\trtl8723be\n"
)
GLXINFO_INTEL = (
    "name of display: :0\nExtended renderer info (GLX_MESA_query_renderer):\n    Vendor: Intel (0x8086)\n"
    "    Accelerated: yes\nOpenGL renderer string: Mesa Intel(R) HD Graphics 400 (BSW)\n"
    "OpenGL version string: 4.6 (Compatibility Profile) Mesa 25.2.8\n"
)
GLXINFO_SOFTWARE = (
    "Extended renderer info (GLX_MESA_query_renderer):\n    Accelerated: no\n"
    "OpenGL renderer string: llvmpipe (LLVM 20.1.2, 256 bits)\n"
)
ASOUND_CARDS = (
    " 0 [PCH            ]: HDA-Intel - HDA Intel PCH\n"
    "                      HDA Intel PCH at 0x91410000 irq 128\n"
    " 1 [Device         ]: USB-Audio - USB Composite Device\n"
    "                      Jieli Technology USB Composite Device at usb-0000:2a:00.3-3, full speed\n"
)
WPCTL = (
    'id 95, type PipeWire:Interface:Node\n  * media.class = "Audio/Sink"\n'
    '  * node.description = "HDA Intel PCH Stéréo analogique"\n  * node.name = "alsa_output.pci-0000_00_1b.0.analog-stereo"\n'
    '  * node.nick = "ALC255 Analog"\n'
)
JOURNAL = (
    "iwlwifi 0000:28:00.0: loaded firmware version 77.f39cc7f9.0 cc-a0-77.ucode op_mode iwlmvm\n"
    "ACPI: [Firmware Bug]: BIOS _OSI(Linux) query ignored\n"
    "r8169 0000:02:00.0: Direct firmware load for rtl_nic/rtl8168h-2.fw failed with error -2\n"
    "r8169 0000:02:00.0: Unable to load firmware rtl_nic/rtl8168h-2.fw (-2)\n"
    "Bluetooth: hci0: Failed to load Intel firmware file intel/ibt-11-5.sfi (-2)\n"
    "r8169 0000:02:00.0: Direct firmware load for rtl_nic/rtl8168h-2.fw failed with error -2\n"
)
UBUNTU_DRIVERS = (
    "== /sys/devices/pci0000:00/0000:00:01.0/0000:01:00.0 ==\n"
    "modalias : pci:v000010DEd00001C82sv00001458sd00003765bc03sc00i00\nvendor   : NVIDIA Corporation\n"
    "model    : GP107 [GeForce GTX 1050 Ti]\ndriver   : nvidia-driver-470 - distro non-free\n"
    "driver   : nvidia-driver-535 - distro non-free recommended\n"
    "driver   : xserver-xorg-video-nouveau - distro free builtin\n\n"
    "== /sys/devices/pci0000:00/0000:00:1c.0/0000:03:00.0 ==\n"
    "model    : BCM4360 802.11ac\ndriver   : bcmwl-kernel-source - distro non-free\n"
)


def runner_returning(outputs: dict[str, str | None]):
    """Un faux `runner` : la sortie dépend du programme (premier élément de argv)."""
    calls: list[list[str]] = []

    def run(argv, timeout=0):
        calls.append(argv)
        return outputs.get(Path(argv[0]).name)

    run.calls = calls
    return run


class OpenGlTests(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(parse_glxinfo(GLXINFO_INTEL), (True, "Mesa Intel(R) HD Graphics 400 (BSW)"))
        self.assertEqual(parse_glxinfo(GLXINFO_SOFTWARE), (False, "llvmpipe (LLVM 20.1.2, 256 bits)"))
        self.assertEqual(parse_glxinfo("OpenGL renderer string: llvmpipe (LLVM 20.1.2)\n"), (False, "llvmpipe (LLVM 20.1.2)"))
        self.assertEqual(parse_glxinfo("Error: unable to open display\n"), (None, ""))

    def test_accelerated(self):
        run = runner_returning({"glxinfo": GLXINFO_INTEL})
        report = check_opengl("/usr/bin/glxinfo", run)
        self.assertEqual(run.calls, [["/usr/bin/glxinfo", "-B"]])
        self.assertEqual((report.status, report.detail), ("ok", "accéléré par la puce (Mesa Intel(R) HD Graphics 400 (BSW))"))

    def test_software_rendering_is_flagged(self):
        report = check_opengl("/usr/bin/glxinfo", runner_returning({"glxinfo": GLXINFO_SOFTWARE}))
        self.assertEqual(report.status, "attention")
        self.assertIn("llvmpipe", report.detail)
        self.assertIn("lspci -k", report.hint)

    def test_missing_tool_or_display(self):
        self.assertEqual(check_opengl(None, runner_returning({})).status, "absent")
        self.assertIn("mesa-utils", check_opengl(None, runner_returning({})).hint)
        report = check_opengl("/usr/bin/glxinfo", runner_returning({"glxinfo": None}))
        self.assertEqual((report.status, report.detail), ("absent", "non vérifiable"))


class PciTests(unittest.TestCase):
    def test_parse_records(self):
        devices = parse_lspci(LSPCI)
        self.assertEqual([d.slot for d in devices], ["00:00.0", "00:02.0", "00:1b.0", "01:00.0"])
        self.assertEqual(devices[1].driver, "i915")
        self.assertEqual(devices[2].modules, ("snd_hda_intel", "snd_soc_avs"))
        self.assertEqual((devices[3].driver, devices[3].modules), ("", ("rtl8723be",)))

    def test_device_without_driver_is_reported_with_its_module(self):
        report = check_pci("/usr/bin/lspci", runner_returning({"lspci": LSPCI}))
        self.assertEqual(report.status, "attention")
        self.assertIn("Network controller « RTL8723BE PCIe Wireless Network Adapter » (module rtl8723be)", report.detail)
        self.assertNotIn("Host bridge", report.detail)  # un pont sans pilote, c'est normal

    def test_all_driven(self):
        driven = LSPCI.replace("Module:\trtl8723be\n", "Driver:\trtl8723be\nModule:\trtl8723be\n")
        report = check_pci("/usr/bin/lspci", runner_returning({"lspci": driven}))
        self.assertEqual((report.status, report.detail), ("ok", "3 appareils pilotés (écran, son, réseau, USB, disques)"))

    def test_missing_lspci(self):
        self.assertEqual(check_pci(None, runner_returning({})).status, "absent")
        self.assertEqual(check_pci("/usr/bin/lspci", runner_returning({"lspci": None})).status, "absent")


class UsbTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sysfs = Path(self.tmp.name)
        self.devices = self.sysfs / "bus" / "usb" / "devices"
        self.devices.mkdir(parents=True)
        (self.sysfs / "bus" / "usb" / "drivers" / "uvcvideo").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, name: str, product: str, interfaces: dict[str, str | None]) -> None:
        """Un appareil et ses interfaces ; la valeur est le pilote attaché, ou None."""
        (self.devices / name).mkdir()
        (self.devices / name / "manufacturer").write_text("Chicony\n")
        (self.devices / name / "product").write_text(product + "\n")
        for suffix, (code, driver) in interfaces.items():
            iface = self.devices / f"{name}:{suffix}"
            iface.mkdir()
            (iface / "bInterfaceClass").write_text(code + "\n")
            if driver:
                os.symlink(self.sysfs / "bus" / "usb" / "drivers" / driver, iface / "driver")

    def test_webcam_without_driver_is_reported_once(self):
        self.add("1-3", "USB2.0 HD UVC WebCam", {"1.0": ("0e", None), "1.1": ("0e", None)})
        self.add("1-4", "Bluetooth Radio", {"1.0": ("e0", "uvcvideo")})
        self.add("1-5", "Lenovo Tab", {"1.0": ("ff", None)})  # classe constructeur : gérée par un programme, pas un pilote
        report = check_usb(self.sysfs)
        self.assertEqual(report.status, "attention")
        self.assertEqual(report.detail, "sans pilote : Chicony USB2.0 HD UVC WebCam (webcam)")

    def test_all_driven(self):
        self.add("1-3", "USB2.0 HD UVC WebCam", {"1.0": ("0e", "uvcvideo")})
        report = check_usb(self.sysfs)
        self.assertEqual((report.status, report.detail), ("ok", "1 interfaces pilotées (son, webcam, Bluetooth, stockage, clavier)"))

    def test_without_sysfs(self):
        self.assertEqual(check_usb(self.sysfs / "nulle-part").status, "absent")


class AudioTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.proc = Path(self.tmp.name)
        (self.proc / "asound").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def write_cards(self, text: str) -> None:
        (self.proc / "asound" / "cards").write_text(text)

    def test_parse(self):
        self.assertEqual(parse_asound_cards(ASOUND_CARDS), ("HDA Intel PCH", "USB Composite Device"))
        self.assertEqual(parse_asound_cards("--- no soundcards ---\n"), ())
        self.assertEqual(parse_wpctl_sink(WPCTL),
                         ("alsa_output.pci-0000_00_1b.0.analog-stereo", "HDA Intel PCH Stéréo analogique"))

    def test_card_and_default_sink(self):
        self.write_cards(ASOUND_CARDS)
        run = runner_returning({"wpctl": WPCTL})
        report = check_audio(self.proc, "/usr/bin/wpctl", "/usr/bin/pactl", run)
        self.assertEqual(run.calls, [["/usr/bin/wpctl", "inspect", "@DEFAULT_AUDIO_SINK@"]])
        self.assertEqual((report.status, report.detail),
                         ("ok", "carte(s) : HDA Intel PCH, USB Composite Device ; sortie : HDA Intel PCH Stéréo analogique"))

    def test_server_without_sink(self):
        self.write_cards(ASOUND_CARDS)
        for output in (None, WPCTL.replace("alsa_output.pci-0000_00_1b.0.analog-stereo", "auto_null")):
            with self.subTest(output=output):
                report = check_audio(self.proc, "/usr/bin/wpctl", None, runner_returning({"wpctl": output}))
                self.assertEqual(report.status, "attention")
                self.assertIn("aucune sortie par défaut", report.detail)

    def test_pactl_fallback_and_no_server_tool(self):
        self.write_cards(ASOUND_CARDS)
        report = check_audio(self.proc, None, "/usr/bin/pactl",
                             runner_returning({"pactl": "Server Name: PulseAudio (on PipeWire 1.0.5)\nDefault Sink: alsa_output.pci-0000_00_1b.0.analog-stereo\n"}))
        self.assertEqual(report.status, "ok")
        self.assertIn("sortie : alsa_output.pci-0000_00_1b.0.analog-stereo", report.detail)
        report = check_audio(self.proc, None, None, runner_returning({}))
        self.assertEqual((report.status, report.detail),
                         ("ok", "carte(s) : HDA Intel PCH, USB Composite Device ; sortie par défaut non vérifiée"))

    def test_no_card(self):
        self.write_cards("--- no soundcards ---\n")
        report = check_audio(self.proc, "/usr/bin/wpctl", None, runner_returning({"wpctl": WPCTL}))
        self.assertEqual((report.status, report.detail), ("attention", "aucune carte son vue par le noyau"))
        self.assertEqual(check_audio(self.proc / "ailleurs", None, None, runner_returning({})).status, "absent")


class FirmwareTests(unittest.TestCase):
    def test_parse_keeps_each_file_once_and_ignores_noise(self):
        self.assertEqual(parse_firmware_failures(JOURNAL),
                         ("rtl_nic/rtl8168h-2.fw", "intel/ibt-11-5.sfi"))
        self.assertEqual(parse_firmware_failures("amdgpu: Found VCN firmware Version ENC: 1.21\n"), ())

    def test_report(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        proc = Path(tmp.name)
        (proc / "uptime").write_text("250.5 1000.0\n")  # démarré il y a 250 s
        run = runner_returning({"journalctl": JOURNAL})
        report = check_firmware("/usr/bin/journalctl", run, proc=proc, now=lambda: 1_000_000.0)
        base = ["/usr/bin/journalctl", "-k", "-b", "-q", "--no-pager", "-o", "cat"]
        self.assertEqual(run.calls, [[*base, "--since", "@999749", "--until", "@1000349"]])  # dix minutes après le démarrage
        self.assertEqual(report.status, "attention")
        self.assertEqual(report.detail, "2 fichier(s) non trouvé(s) au démarrage : rtl_nic/rtl8168h-2.fw, intel/ibt-11-5.sfi")
        self.assertIn("linux-firmware", report.hint)
        run = runner_returning({"journalctl": "usb 1-3: new device\n"})
        clean = check_firmware("/usr/bin/journalctl", run, proc=proc / "sans-uptime")
        self.assertEqual(run.calls, [base])  # sans /proc/uptime : tout le journal du démarrage
        self.assertEqual((clean.status, clean.detail), ("ok", "aucun échec de chargement au démarrage"))

    def test_unreadable_journal_is_not_a_clean_bill(self):
        for output in (None, ""):
            with self.subTest(output=output):
                report = check_firmware("/usr/bin/journalctl", runner_returning({"journalctl": output}))
                self.assertEqual(report.status, "absent")
                self.assertIn("adm", report.hint)
        self.assertEqual(check_firmware(None, runner_returning({})).status, "absent")


class AdditionalDriversTests(unittest.TestCase):
    def test_parse_prefers_recommended_and_skips_builtin(self):
        self.assertEqual(parse_ubuntu_drivers(UBUNTU_DRIVERS),
                         (("GP107 [GeForce GTX 1050 Ti]", "nvidia-driver-535"), ("BCM4360 802.11ac", "bcmwl-kernel-source")))
        self.assertEqual(parse_ubuntu_drivers(""), ())
        only_builtin = "== /sys/devices/x ==\nmodel    : Carte\ndriver   : xserver-xorg-video-nouveau - distro free builtin\n"
        self.assertEqual(parse_ubuntu_drivers(only_builtin), ())

    def test_report(self):
        run = runner_returning({"ubuntu-drivers": UBUNTU_DRIVERS})
        report = check_additional_drivers("/usr/bin/ubuntu-drivers", run)
        self.assertEqual(run.calls, [["/usr/bin/ubuntu-drivers", "devices"]])
        self.assertEqual(report.status, "attention")
        self.assertEqual(report.detail, "proposés : GP107 [GeForce GTX 1050 Ti] → nvidia-driver-535 ; BCM4360 802.11ac → bcmwl-kernel-source")
        self.assertIn("Pilotes additionnels", report.hint)
        clean = check_additional_drivers("/usr/bin/ubuntu-drivers", runner_returning({"ubuntu-drivers": ""}))
        self.assertEqual((clean.status, clean.detail), ("ok", "aucun pilote additionnel proposé"))

    def test_missing(self):
        self.assertEqual(check_additional_drivers(None, runner_returning({})).status, "absent")
        self.assertEqual(check_additional_drivers("/usr/bin/ubuntu-drivers", runner_returning({"ubuntu-drivers": None})).status,
                         "absent")


class ReportTests(unittest.TestCase):
    def test_collect_in_display_order_with_fakes(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "proc" / "asound").mkdir(parents=True)
        (root / "proc" / "asound" / "cards").write_text(ASOUND_CARDS)
        (root / "sys" / "bus" / "usb" / "devices").mkdir(parents=True)
        tools = {"glxinfo": "/usr/bin/glxinfo", "lspci": "/usr/bin/lspci", "wpctl": "/usr/bin/wpctl",
                 "journalctl": "/usr/bin/journalctl", "ubuntu-drivers": "/usr/bin/ubuntu-drivers"}  # pas de vainfo
        run = runner_returning({"glxinfo": GLXINFO_INTEL, "lspci": LSPCI, "wpctl": WPCTL, "journalctl": "rien\n",
                                "ubuntu-drivers": ""})
        report = collect_hardware_report(tools.get, run, sysfs=root / "sys", proc=root / "proc")
        self.assertEqual([c.id for c in report], ["opengl", "decodage", "pci", "usb", "son", "micrologiciels", "additionnels"])
        self.assertEqual([c.status for c in report], ["ok", "absent", "attention", "ok", "ok", "ok", "ok"])
        self.assertTrue(all(c.status in STATUSES for c in report))
        self.assertEqual(sorted(report[0].as_dict()), ["detail", "hint", "id", "label", "status"])
        self.assertEqual(report[1].label, "décodage vidéo matériel")
        self.assertEqual(report[1].detail, "non vérifiable")

    def test_marks_cover_every_status(self):
        self.assertEqual(sorted(hardware.DOCTOR_MARKS), sorted(STATUSES))


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Mesure ce que SigilDesk coûte vraiment : délai d'affichage, mémoire, processeur au repos.

Aucun chiffre n'est promis à l'avance : on mesure sur la machine visée.

    python3 scripts/measure.py                  # lance SigilDesk et mesure 60 s
    python3 scripts/measure.py --duration 120   # repos plus long
    python3 scripts/measure.py --pid 1234       # SigilDesk déjà ouvert (session réelle)

Relevés : délai jusqu'à l'accueil prêt (ligne SIGILDESK_READY), mémoire
résidente (VmRSS) au démarrage puis au repos, mémoire maximale (VmHWM), part
de processeur moyenne au repos (/proc/<pid>/stat). Lire aussi `free -m` avant
et après pour la mémoire disponible de la machine entière.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TICKS = os.sysconf("SC_CLK_TCK")


def status_kb(pid: int, field: str) -> int:
    for line in Path(f"/proc/{pid}/status").read_text().splitlines():
        if line.startswith(field + ":"):
            return int(line.split()[1])
    return 0


def cpu_seconds(pid: int) -> float:
    fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
    return (int(fields[11]) + int(fields[12])) / TICKS  # utime + stime


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pid", type=int, help="mesurer une instance déjà ouverte")
    parser.add_argument("--duration", type=int, default=60, help="durée de la mesure au repos, en secondes")
    parser.add_argument("--json", action="store_true", help="résultat en JSON")
    parser.add_argument("app_args", nargs="*", help="arguments passés à SigilDesk (après --)")
    args = parser.parse_args()

    result: dict = {"machine": os.uname().nodename, "duree_repos_s": args.duration}
    process = None
    if args.pid:
        pid = args.pid
    else:
        venv_python = REPO / ".venv/bin/python"
        python = os.environ.get("SIGILDESK_PYTHON") or (str(venv_python) if venv_python.exists() else sys.executable)
        start = time.monotonic()
        process = subprocess.Popen([python, "-m", "sigildesk", "--print-ready", *args.app_args],
                                   cwd=REPO, stdout=subprocess.PIPE, text=True)
        pid = process.pid
        for line in process.stdout:
            if line.startswith("SIGILDESK_READY"):
                result["accueil_pret_ms"] = round((time.monotonic() - start) * 1000)
                break
        else:
            print("SigilDesk s'est arrêté avant d'être prêt.", file=sys.stderr)
            return 1
        time.sleep(2)
    result["rss_depart_mo"] = round(status_kb(pid, "VmRSS") / 1024, 1)

    cpu0, t0 = cpu_seconds(pid), time.monotonic()
    samples = []
    while time.monotonic() - t0 < args.duration:
        time.sleep(1)
        samples.append(status_kb(pid, "VmRSS"))
    cpu1, t1 = cpu_seconds(pid), time.monotonic()
    result["rss_repos_mo"] = round(samples[-1] / 1024, 1)
    result["rss_max_mo"] = round(status_kb(pid, "VmHWM") / 1024, 1)
    result["cpu_repos_pct"] = round(100 * (cpu1 - cpu0) / (t1 - t0), 2)

    if process:
        process.terminate()
        process.wait(timeout=10)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        rows = []
        if "accueil_pret_ms" in result:
            rows.append(("Accueil prêt en", f"{result['accueil_pret_ms']} ms"))
        rows += [
            ("Mémoire au départ", f"{result['rss_depart_mo']} Mo"),
            (f"Mémoire après {args.duration} s", f"{result['rss_repos_mo']} Mo (maximum {result['rss_max_mo']} Mo)"),
            ("Processeur au repos", f"{result['cpu_repos_pct']} % d'un cœur"),
        ]
        for label, value in rows:
            print(f"{label:<22} : {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

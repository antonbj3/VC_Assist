# -*- coding: utf-8 -*-
"""Kor provsviten mot det som ar COMMITTAT, inte mot arbetstradet.

## Varfor

Repot delas av upp till tolv skrivande agenter. En korning av `pytest
tests/enhet` mot arbetstradet laser filer mitt i nagon annans andring, och
resultatet blir ett rott som inte betyder nagot: halva modulen ar ny och halva
ar gammal, eller en fil ar skriven men dess prov inte an.

Det ar inte olagligt - det ar OLASBART. Ett rott som lika garna kan betyda
"nagon bygger" som "nagot gick sonder" ar ingen grind, for ingen vet vilket
den sager.

Losningen ar att sluta fraga arbetstradet. `git worktree` ger en ren
utcheckning av HEAD i en temporar katalog: allt som ar committat, ingenting som
ar halvskrivet. Rott dar betyder att nagon har committat nagot trasigt, och det
ar ett besked man kan handla pa.

## Vad den INTE gor

Den sager ingenting om otrackat arbete. En agent mitt i ett bygge har rott i
sitt eget trad och gront har, och bada ar sanna om olika saker.

    python3 tests/protocol/kor_svit_mot_head.py [--vag tests/enhet] [--json ut.json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))

BANKPOST = {
    "pastar": "provsviten ar gron mot det som ar committat, inte mot ett "
              "arbetstrad som tolv agenter skriver i samtidigt",
    "under_prov": ("tests/enhet",),
    "facit": "noll roda prov i en ren utcheckning av HEAD",
    "facitkalla": "pytests egen slutkod i en git worktree av HEAD",
    "facitkalla_filer": (),
    "trasiga_fall": (
        "ett rott prov i HEAD ger slutkod 1 och namnger provet",
        "en worktree som inte gick att skapa ger slutkod 2, aldrig ett tyst gront",
    ),
    "kraver": ("inget",),
    "matningar": (),
}

_SAMMANFATTNING = re.compile(
    r"(\d+) (?:passed|failed|error)", re.I)


def _kor(argv, **kw):
    return subprocess.run(argv, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, **kw)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--vag", default="tests/enhet",
                   help="vad som ska koras i utcheckningen")
    p.add_argument("--json")
    a = p.parse_args(argv)

    head = _kor(["git", "-C", _ROT, "rev-parse", "HEAD"])
    if head.returncode != 0:
        print("kunde inte lasa HEAD: %s"
              % head.stdout.decode("utf-8", "replace"), file=sys.stderr)
        return 2
    sha = head.stdout.decode().strip()

    katalog = tempfile.mkdtemp(prefix="vcassist-head-")
    trad = os.path.join(katalog, "trad")
    try:
        # --detach: ingen gren skapas, sa det delade repots grenar ror sig inte.
        skapa = _kor(["git", "-C", _ROT, "worktree", "add", "--detach",
                      trad, sha])
        if skapa.returncode != 0:
            print("kunde inte skapa worktree: %s"
                  % skapa.stdout.decode("utf-8", "replace"), file=sys.stderr)
            return 2

        print("=== PROVSVITEN MOT HEAD ===\n")
        print("  commit: %s" % sha[:12])
        print("  vag:    %s\n" % a.vag)
        t0 = time.time()
        k = _kor([sys.executable, "-m", "pytest", a.vag, "-q", "--no-header",
                  "-p", "no:randomly", "-p", "no:cacheprovider"], cwd=trad)
        ut = k.stdout.decode("utf-8", "replace")
        sekunder = round(time.time() - t0, 1)

        rader = [r for r in ut.splitlines() if r.strip()]
        sista = rader[-1] if rader else ""
        roda = [r for r in rader if r.startswith("FAILED") or r.startswith("ERROR")]
        print("  %s" % sista)
        print("  %.0f s\n" % sekunder)
        if roda:
            print("  ROTT I HEAD - nagon har committat nagot trasigt:")
            for r in roda[:25]:
                print("    %s" % r)
            if len(roda) > 25:
                print("    ... och %d till" % (len(roda) - 25))
        else:
            print("  Gront i HEAD. Ett rott i arbetstradet ar da nagons")
            print("  pagaende arbete, inte en regression.")

        if a.json:
            with open(a.json, "w", encoding="utf-8") as f:
                json.dump({"commit": sha, "vag": a.vag, "slutkod": k.returncode,
                           "sammanfattning": sista, "roda": roda,
                           "sekunder": sekunder}, f, indent=2,
                          ensure_ascii=False)
            print("\n  skrivet: %s" % a.json)
        return 0 if k.returncode == 0 else 1
    finally:
        # Worktreen avregistreras alltid, aven vid avbrott - en kvarglomd
        # worktree i ett delat repo ar en falla for nasta agent.
        _kor(["git", "-C", _ROT, "worktree", "remove", "--force", trad])
        shutil.rmtree(katalog, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

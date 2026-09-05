# -*- coding: utf-8 -*-
"""Hitta processer utan att hitta sig sjalv.

## Varfor modulen finns

Att soka processer pa KOMMANDORADENS TEXT ar en falla som slar tva ganger: den
som soker efter "VisualComponents.Engine" har sjalv den strangen i sin egen
kommandorad, och hittar sig sjalv. Svaret ser riktigt ut - ett pid, en miljo -
och det ar sokarens egen.

Den har fallan har utlost i det har projektet **tre** ganger:

1. `pgrep -f` rapporterade VC igang pa operatorens skarm. Falskt - traffen var
   sokningen sjalv. (Antecknat i minnet, och anda upprepat.)
2. En vantare skriven som `until ! pgrep -f kor_fas9_slingan` vantade pa SIG
   SJALV och snurrade for evigt.
3. 2026-09-05: ett skal-`case` over `/proc/<pid>/cmdline` rapporterade tva
   ganger att en session startat VC med `DISPLAY=:1` pa operatorens skarm.
   Falskt bada gangerna - skalets egen kommandorad bar strangen, och den
   `DISPLAY` som rapporterades var sokarens.

Det tredje ar det dyraste: ett **falsklarm om ett invariantbrott** ar varre an
inget larm, for det flyttar uppmarksamheten till ett fel som inte finns.

## Regeln

**Sok pa BINAREN, inte pa texten.** `/proc/<pid>/exe` ar en symlank till den
korbara filen. En sokare kan inte rakna sig sjalv om den fragar efter ett annat
program an det den sjalv ar.

Behovs kommandoraden anda - VC kors genom `wine`, sa binaren ar `wine` och
programmet star i argumenten - da utesluts sokaren och alla dess foraldrar
uttryckligen. Det ar andra basta och star som sadant.
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional, Sequence


def _las(sokvag: str) -> Optional[str]:
    try:
        with open(sokvag, "rb") as f:
            return f.read().decode("utf-8", "replace")
    except (OSError, IOError):
        return None


def _pids() -> List[int]:
    ut = []
    for namn in os.listdir("/proc"):
        if namn.isdigit():
            ut.append(int(namn))
    return sorted(ut)


def _slakt(pid: Optional[int] = None) -> set:
    """Sokaren sjalv och varje forfader upp till init.

    Foraldrarna maste med: en agent kors av ett skal som kors av en session,
    och bada bar sokstrangen i sina kommandorader.
    """
    ut = set()
    p = os.getpid() if pid is None else pid
    for _ in range(40):
        if p <= 1 or p in ut:
            break
        ut.add(p)
        status = _las("/proc/%d/status" % p)
        if not status:
            break
        mor = None
        for rad in status.splitlines():
            if rad.startswith("PPid:"):
                try:
                    mor = int(rad.split()[1])
                except (IndexError, ValueError):
                    mor = None
                break
        if mor is None:
            break
        p = mor
    return ut


def kommandorad(pid: int) -> str:
    r = _las("/proc/%d/cmdline" % pid)
    return (r or "").replace("\x00", " ").strip()


def miljo(pid: int) -> Dict[str, str]:
    r = _las("/proc/%d/environ" % pid)
    ut = {}
    for post in (r or "").split("\x00"):
        if "=" in post:
            k, v = post.split("=", 1)
            ut[k] = v
    return ut


def binar(pid: int) -> Optional[str]:
    try:
        return os.readlink("/proc/%d/exe" % pid)
    except (OSError, IOError):
        return None


def med_binar(*delstrangar: str) -> List[int]:
    """Pid:ar vars EXE innehaller nagon av delstrangarna.

    Den sakra formen. En sokare kan inte rakna sig sjalv sa lange den fragar
    efter ett annat program an det den kors av.
    """
    ut = []
    for pid in _pids():
        e = binar(pid)
        if e and any(d in e for d in delstrangar):
            ut.append(pid)
    return ut


def med_argument(*delstrangar: str, **kw) -> List[int]:
    """Pid:ar vars KOMMANDORAD innehaller nagon av delstrangarna.

    ANDRA BASTA. Anvands bara nar binaren inte racker - VC kors genom `wine`,
    sa exe ar wine och programmet star i argumenten.

    Sokaren och alla dess foraldrar utesluts ALLTID. `utom` tar extra pid:ar.
    """
    utom = set(kw.get("utom") or ())
    utom |= _slakt()
    ut = []
    for pid in _pids():
        if pid in utom:
            continue
        c = kommandorad(pid)
        if c and any(d in c for d in delstrangar):
            ut.append(pid)
    return ut


# Det program vi oftast fragar efter, och den enda plats dess namn ska sta.
VC_PROGRAM = "VisualComponents.Engine.exe"
VC_BINARER = ("wine-preloader", "/wine")


def vc_processer(bara_prefix: Optional[str] = None) -> List[Dict]:
    """Korande Visual Components, med skarm och prefix.

    Bada leden kravs: binaren ska vara wine OCH argumenten ska namna VC:s exe.
    Sokaren utesluts, sa den kan inte rapportera sin egen miljo som VC:s - det
    felet gjordes 2026-09-05 och ledde till ett falsklarm om att VC startat pa
    operatorens skarm.
    """
    slakt = _slakt()
    ut = []
    for pid in med_binar(*VC_BINARER):
        if pid in slakt:
            continue
        if VC_PROGRAM not in kommandorad(pid):
            continue
        e = miljo(pid)
        post = {"pid": pid,
                "display": e.get("DISPLAY"),
                "wineprefix": e.get("WINEPREFIX")}
        if bara_prefix and post["wineprefix"] != bara_prefix:
            continue
        ut.append(post)
    return ut


def i_operatorens_prefix(operatorens: str = None) -> List[Dict]:
    """VC-processer i operatorens EGNA prefix. Ska alltid vara tomt for oss.

    `90_invarianter.md`: operatorens prefix ror vi aldrig med oprovad kod. Den
    har funktionen gor invarianten fragbar i stallet for ihagkommen.
    """
    if operatorens is None:
        operatorens = os.path.expanduser("~/.wine-vc")
    return [p for p in vc_processer() if p["wineprefix"] == operatorens]

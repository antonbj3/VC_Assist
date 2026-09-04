# -*- coding: utf-8 -*-
"""Parrapporten: ett bänktal publiceras aldrig ensamt, och aldrig mot en annan domare.

`docs/spec/70_faser.md`, fas 11: *"Fas 9:s tal rapporteras alltid som par:
vårt mot baslinjens. Ett tal utan baslinje publiceras inte."* Det står också
varför: `docs/research/R-01_llm_st_och_softplc.md` visade att ingen har
publicerat vår loop, att ingen leverantör publicerar ett korrekthetstal, och
att varje akademiskt tal är kompileringsgrad på en annan uppgiftsmängd. Att
ställa vårt tal mot LLM4PLC:s 72 % vore ett kategorifel.

Den här modulen gör regeln mekanisk i stället för bedd.

## Domarsignaturen, och varför den är hela poängen

Ett par som dömts av två olika domare mäter **domaren**, inte de två sidorna.
Det är samma mätta incident som ligger bakom hela grinddoktrinen: en
omimplementerad positionsdom underkände 2 av 4 medan ögat visade 4 av 4.

`Domarsignatur` binder därför ihop allt som avgör en dom:

* tolkens scanperiod och domarens marginal — två tal som ensamma flyttar var
  en punktavläsning hamnar,
* vilka grindar som faktiskt kördes — en sida som slapp grind 1 har inte
  prövats på samma sak som en som körde den,
* en hash över domarkedjans EGEN källkod — tolken, läsaren, lexern,
  standardbiblioteket, validatorn och de två grindarna,
* en hash över de dömda uppgifternas facit.

Skiljer sig något av det **avvisas paret**. Det går inte att slå av, och det
är avsikten: en jämförelse är antingen mot samma domare eller ingen jämförelse.

## Vad den INTE gör

Den räknar inte om någon dom. Den tar emot två färdiga sidor, prövar att de är
jämförbara, och skriver ut dem bredvid varandra med nämnare. En rapport som
räknar om ett mått mäter till slut sig själv.

beskriver: bank/par.py
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

_HAR = os.path.dirname(os.path.abspath(__file__))
_ROT = os.path.normpath(os.path.join(_HAR, ".."))

# Domarkedjans egen källkod. Ändras en av filerna är det en annan domare, och
# ett tal från i går går inte längre att para med ett tal från i dag.
DOMARKALLOR = (
    "bank/domare.py",
    "svc/vc_assist_svc/st/tolk.py",
    "svc/vc_assist_svc/st/lasare.py",
    "svc/vc_assist_svc/st/lexer.py",
    "svc/vc_assist_svc/st/stdbibliotek.py",
    "svc/vc_assist_svc/st/validator.py",
    "svc/vc_assist_svc/plc/deklarationsgrind.py",
    "svc/vc_assist_svc/plc/stationsgrind.py",
)

# Hur många tecken av sha256 som visas. Bara för läsbarhet i utskriften:
# jämförelsen sker alltid på hela summan.
HASHTECKEN = 12                 # Satt av M-62.


class Parfel(Exception):
    """De två sidorna går inte att jämföra. Kastar hellre än jämför."""


def _filhash(rel: str) -> str:
    with open(os.path.join(_ROT, rel), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def kallhash(kallor: Sequence[str] = DOMARKALLOR) -> str:
    h = hashlib.sha256()
    for rel in sorted(kallor):
        h.update(rel.encode("utf-8"))
        h.update(_filhash(rel).encode("ascii"))
    return h.hexdigest()


def facithash(poster: Sequence[dict]) -> str:
    """Hash över de dömda uppgifternas facit, i uppgiftsordning.

    Facit och inte hela uppgiften: en ändrad prompt ändrar vad sidorna FÅR se,
    men inte vad de döms mot, och två sidor som körts på olika promptar men
    samma facit är fortfarande jämförbara. Att prompten skiljer sig ska stå i
    rapporten, inte fälla den.
    """
    h = hashlib.sha256()
    for post in sorted(poster, key=lambda p: p.get("task_id") or ""):
        h.update((post.get("task_id") or "").encode("utf-8"))
        h.update(json.dumps(post.get("facit_spar") or {}, sort_keys=True,
                            ensure_ascii=True).encode("ascii"))
    return h.hexdigest()


@dataclass(frozen=True)
class Domarsignatur:
    """Allt som avgör en dom. Två sidor med olika signatur är inget par."""

    scan_ms: float
    marginal_scan: int
    grindar: Tuple[str, ...]
    kallor: str
    facit: str
    uppgifter: Tuple[str, ...]

    def kort(self) -> str:
        return "scan %.1f ms, marginal %d scan, grindar [%s], kod %s, facit %s" % (
            self.scan_ms, self.marginal_scan, ", ".join(self.grindar),
            self.kallor[:HASHTECKEN], self.facit[:HASHTECKEN])

    def skillnader(self, annan: "Domarsignatur") -> List[str]:
        ut = []
        for falt in ("scan_ms", "marginal_scan", "grindar", "kallor", "facit",
                     "uppgifter"):
            a, b = getattr(self, falt), getattr(annan, falt)
            if a != b:
                ut.append("%s: %r mot %r" % (falt, a, b))
        return ut


def signatur(poster: Sequence[dict], grindar: Sequence[str],
             scan_ms: Optional[float] = None,
             marginal_scan: Optional[int] = None) -> Domarsignatur:
    """Signaturen för en körning över `poster` med `grindar`."""
    import sys
    if os.path.join(_ROT, "svc") not in sys.path:
        sys.path.insert(0, os.path.join(_ROT, "svc"))
    if _HAR not in sys.path:
        sys.path.insert(0, _HAR)
    import domare as _domare
    from vc_assist_svc.st import tolk as _tolk
    return Domarsignatur(
        scan_ms=float(_tolk.SCAN_MS if scan_ms is None else scan_ms),
        marginal_scan=int(_domare.MARGINAL_SCAN if marginal_scan is None
                          else marginal_scan),
        grindar=tuple(grindar),
        kallor=kallhash(),
        facit=facithash(poster),
        uppgifter=tuple(sorted(p.get("task_id") or "" for p in poster)))


@dataclass
class Sida:
    """En sida av paret: ett namn, en signatur och ett utfall per uppgift.

    `utfall` är {task_id: bool} — klarade domen eller inte. `detaljer` är fritt
    och skrivs bara ut; det får aldrig påverka jämförelsen.
    """

    namn: str
    signatur: Domarsignatur
    utfall: Dict[str, bool] = field(default_factory=dict)
    klasser: Dict[str, int] = field(default_factory=dict)
    detaljer: Dict[str, object] = field(default_factory=dict)

    @property
    def antal(self) -> int:
        return len(self.utfall)

    @property
    def klarade(self) -> int:
        return sum(1 for v in self.utfall.values() if v)


@dataclass
class Parrapport:
    vanster: Sida
    hoger: Sida

    def text(self) -> str:
        v, h = self.vanster, self.hoger
        rader = ["PAR: %s mot %s" % (v.namn, h.namn),
                 "DOMARE: %s" % v.signatur.kort(),
                 "",
                 "%-28s %-16s %-16s" % ("storhet", v.namn, h.namn),
                 "%-28s %-16s %-16s"
                 % ("klarade domen",
                    "%d av %d" % (v.klarade, v.antal),
                    "%d av %d" % (h.klarade, h.antal))]
        rader.append("")
        rader.append("PER UPPGIFT")
        for tid in sorted(set(v.utfall) | set(h.utfall)):
            rader.append("%-28s %-16s %-16s"
                         % (tid, _ja(v.utfall.get(tid)), _ja(h.utfall.get(tid))))
        klasser = sorted(set(v.klasser) | set(h.klasser))
        if klasser:
            rader.append("")
            rader.append("FEL PER KLASS (antal uppgifter som fallde pa klassen)")
            for klass in klasser:
                rader.append("%-28s %-16s %-16s"
                             % (klass,
                                "%d av %d" % (v.klasser.get(klass, 0), v.antal),
                                "%d av %d" % (h.klasser.get(klass, 0), h.antal)))
        return "\n".join(rader)


def _ja(varde) -> str:
    if varde is None:
        return "-"
    return "klarade" if varde else "fallde"


def para(vanster: Sida, hoger: Sida) -> Parrapport:
    """Paret, eller ett Parfel. Det finns ingen väg förbi kontrollen.

    Trasig fixtur: `tests/enhet/test_baslinje.py` kör två sidor dömda med olika
    scanperiod och kräver att den här funktionen kastar. Utan den fixturen är
    regeln en bön i en docstring.
    """
    skillnader = vanster.signatur.skillnader(hoger.signatur)
    if skillnader:
        raise Parfel(
            "sidorna %r och %r ar domda av OLIKA domare och gar inte att "
            "jamfora:\n  %s\nEn jamforelse mellan tva domare mater domaren, "
            "inte de tva sidorna (70_faser.md fas 11)."
            % (vanster.namn, hoger.namn, "\n  ".join(skillnader)))
    if not vanster.utfall or not hoger.utfall:
        raise Parfel("en sida utan utfall ar ingen sida; %r har %d och %r har %d"
                     % (vanster.namn, len(vanster.utfall), hoger.namn,
                        len(hoger.utfall)))
    return Parrapport(vanster, hoger)

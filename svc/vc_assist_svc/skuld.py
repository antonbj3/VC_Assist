# -*- coding: utf-8 -*-
"""Skuldregistret: teknisk skuld fangad NAR den skrivs, inte vid en senare granskning.

Operatorens krav: "Kom ihag nu att reviewa och halla koll pa mojlig teknisk
skuld och saker som senare behover goras om" - och skarpningen: "Vi fangar det
at moment of writing foredragsvis."

VARFOR REGISTRET GENERERAS OCH INTE FORS
----------------------------------------
Ett register nagon maste komma ihag att uppdatera ar redan glomt. Den enda
skulden som hamnar i ett sadant register ar den man ando kom ihag, alltsa inte
den farliga.

Darfor for ingen det har registret. Det HARVAS ur det som redan skrivs:

  * matningarnas arlighetsavsnitt - "Vad som INTE ar matt", "Vad som inte ar
    provat", "Vad detta INTE bevisar" och deras syskon. Disciplinen finns redan
    (MATT: 30 av 43 matningar bar ett sadant avsnitt), och den skrivs samtidigt
    som matningen. Det ar precis "moment of writing".
  * markorer i koden - PRELIMINAR, "inte lagat", "oppen punkt", "kvar som",
    "oprovad". De skrivs ocksa i samma andetag som koden.

Foljden ar att skulden inte kan glida ifran verkligheten: andrar nagon en
matning andras registret nasta gang det byggs, och tar nagon bort ett
arlighetsavsnitt SYNS det som en minskning som lintern faller pa.

VAD REGISTRET INTE ER
---------------------
Det ar ingen prioriteringslista och ingen plan. Det ar en sammanstallning av
vad vi redan har skrivit att vi inte vet. Att bedoma vad som ska goras forst ar
ett annat arbete, och det ska inte smyga in har.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

# Rubrikerna som markerar ett arlighetsavsnitt. Listan ar MATT ur de 43
# matningarna som fanns 2026-09-04, inte paahittad - se M-66. Den ar medvetet
# bred: en matning som skriver "Vad som fortfarande inte fungerar" har gjort
# ratt sak, och ska inte falla pa att den valde ett annat ord.
_ARLIGHET = re.compile(
    r"^#{2,4}\s+"
    # Rubriken kan bara ett nummer eller en fallkod forst: "## 9. Vad som ..."
    # eller "### F9. Sadant som ...". MATT: bada formerna finns i repot, och en
    # regex som kraver att rubriken borjar med ordet missar dem tyst.
    r"(?:[0-9]+\.|[A-ZF][0-9]+\.|\d+\.\d+)?\s*"
    r"(?:"
    r"vad\s+(?:som\s+)?(?:detta\s+|de\s+har\s+|lintern\s+|tolken\s+|"
    r"rattelserna\s+|jag\s+)?(?:medvetet\s+)?(?:inte|INTE)\b.*"
    r"|vad\s+som\s+(?:fortfarande\s+)?inte\b.*"
    r"|vad\s+som\s+ligger\s+utanfor\b.*"
    r"|fynd\s+jag\s+(?:inte|INTE)\b.*"
    r"|.*\boprovat?\b.*"
    r"|.*\bobevisad[et]?\b.*"
    r"|.*\boppna?\s+(?:punkter|fraga|fragor)\b.*"
    r"|.*\bkvar\s+att\s+gora\b.*"
    r"|rackvidd(?:en)?\s*$"
    r"|.*\bforbehall\b.*"
    r"|.*\bbegransningar?\b.*"
    r")$",
    re.I | re.M)

# Markorer i kod och dokument som betyder "det har ar inte fardigt".
_KODMARKOR = re.compile(
    r"\b(PRELIMIN[AÄ]R|TODO|FIXME|XXX|oprovad[et]?|inte lagat|inte lagad[et]?|"
    r"oppen punkt|öppen punkt|kvar som en uttalad|inte provat|inte prövat)\b",
    re.I)

# Filer som INTE ska genomsokas efter kodmarkorer. Registret sjalvt och dess
# prov namner markorerna for att kunna kanna igen dem, och skulle annars
# rapportera sig sjalvt - en grind som far sin egen utdata som indata.
_UNDANTAG = ("skuld.py", "test_skuld.py", "SKULDREGISTER.md",
             "TROSKELSKULD.md", "M-66")


@dataclass
class Post:
    """En skuldpost: var den star, vad den sager."""

    kalla: str
    sort: str          # "matning" eller "kod"
    rubrik: str
    rader: List[str] = field(default_factory=list)

    @property
    def antal(self) -> int:
        return len(self.rader)


def _undantagen(sokvag: str) -> bool:
    return any(u in sokvag for u in _UNDANTAG)


def ur_matning(sokvag: str) -> List[Post]:
    """Arlighetsavsnitten i en matning, med sina punkter."""
    with open(sokvag, "r", encoding="utf-8") as f:
        text = f.read()
    rader = text.splitlines()
    ut: List[Post] = []
    i = 0
    while i < len(rader):
        rad = rader[i]
        if _ARLIGHET.match(rad):
            niva = len(rad) - len(rad.lstrip("#"))
            punkter: List[str] = []
            j = i + 1
            while j < len(rader):
                nasta = rader[j]
                if nasta.startswith("#"):
                    n2 = len(nasta) - len(nasta.lstrip("#"))
                    if n2 <= niva:
                        break
                if nasta.strip().startswith(("*", "-")):
                    punkter.append(nasta.strip().lstrip("*- ").strip())
                j += 1
            ut.append(Post(os.path.basename(sokvag), "matning",
                           rad.lstrip("# ").strip(), punkter))
            i = j
            continue
        i += 1
    return ut


def ur_kod(rot: str, andelser=(".py", ".mjs")) -> List[Post]:
    """Markorer i koden. En rad per traff, med sin egen text."""
    ut: List[Post] = []
    for katalog, kataloger, filer in os.walk(rot):
        kataloger[:] = [k for k in kataloger
                        if k not in ("__pycache__", ".git", "node_modules")]
        for f in sorted(filer):
            if not f.endswith(andelser):
                continue
            sokvag = os.path.join(katalog, f)
            if _undantagen(sokvag):
                continue
            try:
                with open(sokvag, "r", encoding="utf-8") as fh:
                    rader = fh.read().splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            traffar = [("%s:%d" % (os.path.relpath(sokvag, rot), n + 1),
                        r.strip())
                       for n, r in enumerate(rader) if _KODMARKOR.search(r)]
            if traffar:
                ut.append(Post(os.path.relpath(sokvag, rot), "kod", "markorer",
                               ["%s  %s" % (var, txt) for var, txt in traffar]))
    return ut


def matningar_utan_arlighetsavsnitt(katalog: str) -> List[str]:
    """De matningar som inte sager nagot om vad de INTE visar.

    En matning utan ett sadant avsnitt ar inte en matning utan skuld - den ar
    en matning vars skuld ingen har skrivit ned. Samma resonemang som
    guldgrindens krav pa HONESTY: regeln ar TOM om sektionen inte finns.
    """
    ut = []
    for f in sorted(os.listdir(katalog)):
        if not (f.startswith("M-") and f.endswith(".md")):
            continue
        if not ur_matning(os.path.join(katalog, f)):
            ut.append(f)
    return ut


def moduler_utan_prov(rot: str) -> Dict[str, List[Tuple[str, int]]]:
    """Produktionsmoduler efter vilken sorts prov som namner dem.

    Tva hinkar, och skillnaden ar inte kosmetisk:

      "inget"     ingen provfil alls namner modulen. Med sakerhet oprovad.
      "bara_l3"   bara en korning under tests/protocol/ namner den. Sadana
                  kraver levande VC, OpenPLC eller kompilator och kors INTE av
                  `pytest tests/enhet`. En modul i den hinken gar alltsa inte
                  att kontrollera pa en ren maskin, och det ar en annan sorts
                  skuld an ingen tackning alls - men det ar skuld.

    Kriteriet ar med flit grovt: namns modulens filnamn i provtexten? Ett finare
    matt hade varit battre och dyrare, och det grova fangar redan det som ska
    fangas.

    __init__.py raknas inte: den ar limmet och provas genom det den binder.
    """
    def las(katalog):
        text = []
        for kat, kataloger, filer in os.walk(katalog):
            kataloger[:] = [k for k in kataloger if k != "__pycache__"]
            for f in filer:
                if f.endswith((".py", ".md")):
                    try:
                        with open(os.path.join(kat, f), "r",
                                  encoding="utf-8") as fh:
                            text.append(fh.read())
                    except (OSError, UnicodeDecodeError):
                        pass
        return "\n".join(text)

    enhet = las(os.path.join(rot, "tests", "enhet"))
    protokoll = las(os.path.join(rot, "tests", "protocol"))
    ovrigt = ""
    tests = os.path.join(rot, "tests")
    if os.path.isdir(tests):
        for post in sorted(os.listdir(tests)):
            hel = os.path.join(tests, post)
            if os.path.isdir(hel) and post not in ("enhet", "protocol",
                                                   "__pycache__"):
                ovrigt += las(hel)

    ut = {"inget": [], "bara_l3": []}
    for under in ("svc", "ext", "bank", "install"):
        bas = os.path.join(rot, under)
        if not os.path.isdir(bas):
            continue
        for katalog, kataloger, filer in os.walk(bas):
            kataloger[:] = [k for k in kataloger
                            if k not in ("__pycache__", "node_modules")]
            for f in sorted(filer):
                if not f.endswith(".py") or f == "__init__.py":
                    continue
                stam = os.path.splitext(f)[0]
                sokvag = os.path.relpath(os.path.join(katalog, f), rot)
                try:
                    n = sum(1 for _ in open(os.path.join(rot, sokvag),
                                            encoding="utf-8"))
                except (OSError, UnicodeDecodeError):
                    n = 0
                if stam in enhet or stam in ovrigt:
                    continue
                if stam in protokoll:
                    ut["bara_l3"].append((sokvag, n))
                else:
                    ut["inget"].append((sokvag, n))
    ut["inget"].sort()
    ut["bara_l3"].sort()
    return ut


def bygg(rot: str) -> Dict[str, object]:
    matningar = os.path.join(rot, "docs", "matningar")
    poster: List[Post] = []
    for f in sorted(os.listdir(matningar)):
        if f.startswith("M-") and f.endswith(".md") and not _undantagen(f):
            poster.extend(ur_matning(os.path.join(matningar, f)))
    kodposter: List[Post] = []
    for under in ("svc", "ext", "install", "bank", "tests"):
        katalog = os.path.join(rot, under)
        if os.path.isdir(katalog):
            kodposter.extend(ur_kod(katalog))
    return {
        "matningsposter": poster,
        "kodposter": kodposter,
        "utan_arlighetsavsnitt": matningar_utan_arlighetsavsnitt(matningar),
        "moduler_utan_prov": moduler_utan_prov(rot),
        "antal_punkter": sum(p.antal for p in poster),
        "antal_kodmarkorer": sum(p.antal for p in kodposter),
    }


def text(register: Dict[str, object]) -> str:
    rader = ["# Skuldregistret",
             "",
             "**Genererat**, aldrig fört för hand. Ett register någon måste "
             "komma ihåg att uppdatera är redan glömt, och den enda skuld som "
             "hamnar där är den man ändå kom ihåg.",
             "",
             "Byggs med `python3 -m vc_assist_svc.skuld` ur två källor som "
             "båda skrivs samtidigt som arbetet: mätningarnas ärlighetsavsnitt "
             "och markörer i koden.",
             ""]
    utan = register["utan_arlighetsavsnitt"]
    rader.append("## Mätningar utan ärlighetsavsnitt: %d" % len(utan))
    rader.append("")
    if utan:
        rader.append("En mätning utan ett sådant avsnitt är inte en mätning "
                     "utan skuld — det är en mätning vars skuld ingen har "
                     "skrivit ned.")
        rader.append("")
        for f in utan:
            rader.append("* `%s`" % f)
        rader.append("")
    rader.append("## Vad mätningarna säger att de inte vet: %d punkter"
                 % register["antal_punkter"])
    rader.append("")
    for p in register["matningsposter"]:
        if not p.rader:
            continue
        rader.append("### %s — %s" % (p.kalla, p.rubrik))
        rader.append("")
        for r in p.rader:
            rader.append("* %s" % r)
        rader.append("")
    utan_prov = register.get("moduler_utan_prov") or {"inget": [], "bara_l3": []}
    for nyckel, rubrik in (
            ("inget", "Produktionsmoduler som ingen provfil nämner"),
            ("bara_l3", "Produktionsmoduler som bara nämns av en L3-körning "
                        "(kräver VC/OpenPLC, körs inte av `pytest tests/enhet`)")):
        lista = utan_prov.get(nyckel) or []
        rader.append("## %s: %d (%d rader)"
                     % (rubrik, len(lista), sum(n for _f, n in lista)))
        rader.append("")
        for f, n in lista:
            rader.append("* `%s` — %d rader" % (f, n))
        rader.append("")
    rader.append("## Markörer i koden: %d" % register["antal_kodmarkorer"])
    rader.append("")
    for p in register["kodposter"]:
        rader.append("### %s" % p.kalla)
        rader.append("")
        for r in p.rader:
            rader.append("* %s" % r)
        rader.append("")
    return "\n".join(rader) + "\n"


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(description="Bygg skuldregistret.")
    p.add_argument("--rot", default=os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
    p.add_argument("--ut", default=None)
    a = p.parse_args(argv)
    reg = bygg(a.rot)
    print("%d punkter ur %d matningsavsnitt, %d kodmarkorer i %d filer, "
          "%d matningar utan arlighetsavsnitt"
          % (reg["antal_punkter"], len(reg["matningsposter"]),
             reg["antal_kodmarkorer"], len(reg["kodposter"]),
             len(reg["utan_arlighetsavsnitt"])))
    if a.ut:
        with open(a.ut, "w", encoding="utf-8") as f:
            f.write(text(reg))
        print("skrivet: %s" % a.ut)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

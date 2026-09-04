# -*- coding: utf-8 -*-
"""Efterlevnadsbanken: kor fallorna och rapporterar TAL.

Instruktioner som inte mats efterlevs inte. Banken kor varje falla i
fallor.py genom den RIKTIGA harnessen - riktiga grindar, riktigt register,
riktigt API-index, riktig skrivgrind - mot en attrappmodell och en
attrappkanal. Det enda som ar attrapp ar varlden, aldrig grinden.

Tre tal rapporteras, och de ar tre olika storheter:

  FANGADE          fallor dar harnessens utfall ar EXAKT det facit sager
  FANGAD AV FEL GRIND  harnessen stoppade, men en annan grind fallde an den
                   som skulle. Det ar inte ett godkant fangst: klassningen
                   blir fel i felstatistiken (82_felklasser.md), och den
                   grind som SKULLE ha fallt star fortfarande oprovad.
  SLUPPNA          fallor som gick rakt igenom

Och skilt fran dem, aldrig hopraknat med dem:

  FALSKA AVVISNINGAR   kontrollfall som fastnade. En harness som avvisar
                       allt ser lika bra ut som en som fangar allt, om man
                       bara raknar avvisningar.
  EJ MEKANISKA         fallor vars facit ar att harnessen INTE kan fanga
                       dem. De raknas for sig och namns vid namn.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from . import fallor as Fa
from . import mekanismer as Mk
from .fallor import ALLA, EJ_MEKANISK, Falla
from .forgranskning import Forgranskare
from .instruktioner import Korpus, las_korpus
from .kanal import Attrappkanal
from .loop import Harness, Turprotokoll
from .modell import AttrappModell
from .sakerhet import Sakerhetsgrind

# Utfall som betyder att harnessen stoppade nagot.
_STOPPADE = ("AVVISAD", "OMSKRIVNING", "STOPP")


@dataclass(frozen=True)
class Rad:
    """En falla, korned."""

    falla: Falla
    faktiskt: str
    protokoll: Turprotokoll

    @property
    def stoppad(self) -> bool:
        return self.faktiskt.split(":")[0] in _STOPPADE

    @property
    def traff(self) -> bool:
        """Sant nar harnessen gjorde exakt det facit foreskriver."""
        if self.falla.facit == EJ_MEKANISK:
            return not self.stoppad
        return self.faktiskt == self.falla.facit

    @property
    def fel_grind(self) -> bool:
        return (self.falla.facit != EJ_MEKANISK and self.stoppad
                and self.faktiskt != self.falla.facit)

    def rad(self) -> str:
        markor = "OK " if self.traff else ("GRIND" if self.fel_grind else "MISS")
        return "%s %-5s %-12s facit=%-38s faktiskt=%s" % (
            self.falla.id, markor, self.falla.klass, self.falla.facit,
            self.faktiskt)


@dataclass
class Bankresultat:
    rader: List[Rad] = field(default_factory=list)

    # ---- urval ----------------------------------------------------------

    @property
    def mekaniska(self) -> List[Rad]:
        return [r for r in self.rader
                if not r.falla.kontroll and r.falla.mekanisk]

    @property
    def ej_mekaniska(self) -> List[Rad]:
        return [r for r in self.rader if r.falla.facit == EJ_MEKANISK]

    @property
    def kontrollfall(self) -> List[Rad]:
        return [r for r in self.rader if r.falla.kontroll]

    # ---- tal ------------------------------------------------------------

    @property
    def fangade(self) -> int:
        return sum(1 for r in self.mekaniska if r.traff)

    @property
    def fel_grind(self) -> int:
        return sum(1 for r in self.mekaniska if r.fel_grind)

    @property
    def sluppna(self) -> List[Rad]:
        return [r for r in self.mekaniska if not r.stoppad]

    @property
    def falska_avvisningar(self) -> List[Rad]:
        return [r for r in self.kontrollfall if not r.traff]

    def per_klass(self) -> Dict[str, Tuple[int, int]]:
        ut: Dict[str, List[int]] = {}
        for r in self.mekaniska:
            post = ut.setdefault(r.falla.klass, [0, 0])
            post[1] += 1
            if r.traff:
                post[0] += 1
        return {k: (v[0], v[1]) for k, v in sorted(ut.items())}

    def per_mekanism(self) -> Dict[str, Tuple[int, int]]:
        ut: Dict[str, List[int]] = {}
        for r in self.mekaniska:
            post = ut.setdefault(r.falla.mekanism or "-", [0, 0])
            post[1] += 1
            if r.traff:
                post[0] += 1
        return {k: (v[0], v[1]) for k, v in sorted(ut.items())}

    @property
    def helt_gron(self) -> bool:
        """Alla mekaniska fallor fangade och inget kontrollfall fallt."""
        return (self.fangade == len(self.mekaniska)
                and not self.falska_avvisningar)

    # ---- rapport --------------------------------------------------------

    def text(self) -> str:
        rader = ["EFTERLEVNADSBANKEN", ""]
        rader += [r.rad() for r in self.rader]
        rader += ["",
                  "FALLOR (mekaniska): %d av %d fangade, %d fangade av fel "
                  "grind, %d slapp igenom"
                  % (self.fangade, len(self.mekaniska), self.fel_grind,
                     len(self.sluppna))]
        rader.append("PER KLASS:")
        for klass, (fangade, totalt) in self.per_klass().items():
            rader.append("  %-12s %d av %d" % (klass, fangade, totalt))
        rader.append("PER MEKANISM:")
        for mekanism, (fangade, totalt) in self.per_mekanism().items():
            vad = (Mk.beskrivning(mekanism).split(":")[0]
                   if mekanism in Mk.MEKANISMER else "")
            rader.append("  %-12s %d av %d   %s" % (mekanism, fangade, totalt,
                                                    vad))
        rader.append("KONTROLLFALL: %d av %d slapptes igenom, %d falska "
                     "avvisningar"
                     % (len(self.kontrollfall) - len(self.falska_avvisningar),
                        len(self.kontrollfall), len(self.falska_avvisningar)))
        for r in self.falska_avvisningar:
            rader.append("  FALSK AVVISNING %s: %s" % (r.falla.id, r.faktiskt))
        rader.append("EJ MEKANISKT FANGBARA: %d, och de raknas inte som "
                     "fangade" % len(self.ej_mekaniska))
        for r in self.ej_mekaniska:
            rader.append("  %s: %s" % (r.falla.id,
                                       r.falla.beskrivning.split(".")[0]))
        for r in self.sluppna:
            rader.append("  SLAPP IGENOM %s (%s): facit var %s"
                         % (r.falla.id, r.falla.klass, r.falla.facit))
            # Hela turen skrivs ut for den som slapp igenom. En siffra utan
            # sin korning gar inte att felsoka.
            rader.append("    " + r.protokoll.text().replace("\n", "\n    "))
        for r in self.mekaniska:
            if r.fel_grind:
                rader.append("  FEL GRIND %s: facit %s, faktiskt %s"
                             % (r.falla.id, r.falla.facit, r.faktiskt))
        return "\n".join(rader)


class Bank(object):
    """Banken. Bygger de dyra delarna EN gang och kor sedan fallorna."""

    def __init__(self, korpus: Optional[Korpus] = None,
                 forgranskare: Optional[Forgranskare] = None):
        self.korpus = las_korpus() if korpus is None else korpus
        # API-indexet ar det dyra (fyra filer under docs/referens/). Bada
        # forgranskarna delar samma validator, sa det byggs en gang.
        self.utan_karta = (Forgranskare() if forgranskare is None
                           else forgranskare)
        self.med_karta = Forgranskare(
            validator=self.utan_karta.validator,
            sakerhetsgrind=Sakerhetsgrind(
                signalkarta=Fa.SIGNALKARTA,
                katalogindex=self.utan_karta.katalogindex))

    def kor_en(self, falla: Falla) -> Rad:
        modell = AttrappModell(falla.svar, namn="attrapp-%s" % falla.id)
        kanal = Attrappkanal(falla.manus)
        harness = Harness(
            modell=modell, kanal=kanal, korpus=self.korpus,
            forgranskare=(self.med_karta if falla.med_signalkarta
                          else self.utan_karta))
        protokoll = harness.kor(falla.uppgift,
                                ogonrapport=falla.ogonrapport,
                                guldbeslut=falla.guld)
        return Rad(falla=falla, faktiskt=protokoll.utfall, protokoll=protokoll)

    def kor(self, fallor: Sequence[Falla] = ALLA) -> Bankresultat:
        return Bankresultat([self.kor_en(f) for f in fallor])


def kor_bank(fallor: Sequence[Falla] = ALLA,
             korpus: Optional[Korpus] = None,
             forgranskare: Optional[Forgranskare] = None) -> Bankresultat:
    """Kor hela banken. Konsument: tests/enhet/test_efterlevnad.py och main."""
    return Bank(korpus=korpus, forgranskare=forgranskare).kor(fallor)


def main(argv: Optional[Sequence[str]] = None) -> int:
    resultat = kor_bank()
    print(resultat.text())
    # Fail-closed aven har: banken lamnar 1 sa fort en falla slipper igenom
    # eller ett kontrollfall falls, sa att den kan hanga i ett bygge.
    return 0 if resultat.helt_gron else 1


if __name__ == "__main__":
    sys.exit(main())

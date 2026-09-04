# -*- coding: utf-8 -*-
"""HONESTY-REWRITE: ett svar som pastar framgang medan ett verktyg foll.

Arvd ur Isaac Assist och OBLIGATORISK (docs/spec/20_arv.md). Mekanismen finns
och fungerar i kallan, och den ar den enda som fangar just den lognen: sista
verktyget failade, och svaret sager "klart".

TVA REGLER, och den andra ar var egen:

  arlighet_sista_verktyget
      Den arvda. Sista verktygsanropet i turen foll, och slutsvaret bar ett
      framgangspastaende utan att namna ett fel.

  arlighet_onamnt_fel
      Vidare an arvet, och motiverad av S1 i 96_ingen_skuld.md: ett verktyg
      NAGONSTANS i turen foll, och slutsvaret namner inte ett enda fel. Det
      ar samma logn i langsam form - en modell som gor tre anrop, tappar det
      andra och sammanfattar de tva som lyckades. Sista anropet lyckades, sa
      den arvda regeln ser den inte.

Grinden anklagar aldrig pa svag grund: ett framgangspastaende maste bara en
tydlig markor (text.FRAMGANGSMARKORER) och far inte samtidigt namna ett fel.
Klassningen av en mening som PASTAENDE ar daremot fail-closed. Skalen for
bada halvorna star i text.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Sequence, Tuple

from .text import framgangspastaenden, namner_fel

KODER = ("arlighet_sista_verktyget", "arlighet_onamnt_fel")


@dataclass(frozen=True)
class Anmarkning:
    kod: str
    skal: str
    mening: str = ""

    def text(self) -> str:
        if self.mening:
            return "%s: %s (i meningen: %r)" % (self.kod, self.skal, self.mening)
        return "%s: %s" % (self.kod, self.skal)


def _felbeskrivning(utfall: Any) -> str:
    fel = getattr(utfall, "fel", "") or "utan angivet skal"
    return "%s foll: %s" % (getattr(utfall, "verktyg", "verktyget"), fel)


def granska(text: str, utfall: Sequence[Any]) -> Tuple[Anmarkning, ...]:
    """Provar slutsvaret mot turens verktygsutfall.

    utfall ar turens anropsutfall i ordning. Varje post ska ha .ok, .verktyg
    och .fel; mer an sa lite kraver grinden inte, sa att den kan provas pa
    syntetiska utfall utan att nagot kors (L1, 95_testprotokoll.md).
    """
    if not utfall:
        return ()
    anmarkningar: List[Anmarkning] = []
    pastaenden = framgangspastaenden(text)

    sista = utfall[-1]
    if not sista.ok and pastaenden:
        anmarkningar.append(Anmarkning(
            kod="arlighet_sista_verktyget",
            skal=("svaret pastar framgang medan sista verktyget foll (%s)"
                  % _felbeskrivning(sista)),
            mening=pastaenden[0].text))

    fallda = [u for u in utfall if not u.ok]
    if fallda and not namner_fel(text):
        anmarkningar.append(Anmarkning(
            kod="arlighet_onamnt_fel",
            skal=("%d av %d verktygsanrop foll (%s) och slutsvaret namner "
                  "inte ett enda fel"
                  % (len(fallda), len(utfall),
                     "; ".join(_felbeskrivning(u) for u in fallda[:3])))))
    return tuple(anmarkningar)


def omskrivningskrav(anmarkningar: Sequence[Anmarkning]) -> str:
    """Texten tillbaka till modellen. Namner felet, aldrig bara att det finns."""
    rader = ["Svaret godkanns inte. Det ar inte arligt om vad som hande:"]
    for a in anmarkningar:
        rader.append("  - %s" % a.text())
    rader.append(
        "Skriv om svaret. Namnge verktyget som foll, felet det gav och vad du "
        "darfor INTE kunde gora. Pasta inte att uppgiften ar klar nar den inte "
        "ar det - en ofardig vag redovisas som ofardig (ARL-001, ARL-004).")
    return "\n".join(rader)

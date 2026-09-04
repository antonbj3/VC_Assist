# -*- coding: utf-8 -*-
"""Grinden över förloppsytan: dömer PARET protokoll och text.

Varför en grind över en visning över huvud taget? Därför att en visning är en
dom om systemets tillstånd, ställd till den enda som inte kan kontrollera den.
Vi som bygger kan läsa loggen. Användaren kan bara läsa ytan. En yta som
säger fel har därför en värre asymmetri än en logg som säger fel.

Grinden tar två saker: `Forlopp` (vad som faktiskt hände) och den TEXT en
renderare producerade. Den dömer aldrig protokollet mot sig självt — den
dömer texten mot protokollet. Det är hela poängen: den fäller också en
renderare som inte är skriven än. Bygger vi en webbsida en dag är det den här
grinden som vaktar den, utan en rad ny kod.

## Reglerna, och den mätta incident var och en kommer ur

**Y1  Läget står först, ordagrant.** Ett läge som går att läsa fel är ett läge
som kommer att läsas fel.

**Y2  Ett stilla läge visar ingen pågåendemarkör.** Det är fasens egen
trasiga fixtur: *"ett fällt läge får aldrig se ut som ett arbetande"*. Samma
felklass kopplaren skyddar mot när den ger upp efter tre raka fel i stället
för att mala vidare och se ut att arbeta (M-39).

**Y3  Fallets skäl står ordagrant.** "Något gick fel" är inget besked.

**Y4  Varje främmande sträng når användaren tecken för tecken.** Doktrinen ur
`50_grindar.md`, motiverad av en mätt incident: en omimplementerad
positionsdom underkände 2 av 4 medan ögat visade 4 av 4. En omskrivning på
vägen till användaren är samma fel som en omskrivning på vägen till modellen,
och `reparation.kontrollera_ordagrant` mekaniserar redan den andra halvan.

**Y5  Avsnittet om vad systemet inte vet finns, och är aldrig tomt.**
Räckvidden i `50_grindar.md` gäller varje körning. Ögat är felfinnande,
aldrig bevis.

**Y6  En dom utan obligatorisk sektion visas inte som en dom.** Samma regel
guldgrinden redan har: en rapport utan `HONESTY` har ingen ärlighetsgrind
alls, och den såg ut som guld.

**Y7  Guld visas aldrig utan ögondom.** Regel A-6 i `26_appen.md`.

**Y8  Trimningen säger hur mycket den dolde.** M-60:s regel: ett svar som
inte säger vad det inte visade ser uttömmande ut.

**Y9  Ett hjärtslag räknas aldrig som framsteg.** Gör det det blir en död
körning odödlig — mätt i M-64.

**Y10 Ett arbetande läge namnger vad som pågår och hur länge.** `26_appen.md`
§5 punkt 3 förbjuder en framstegsindikator utan en mätt storhet bakom sig.

**Y11 En avslutad körning räknar stegen som aldrig kördes.** Ett levererat
svar över en halvkörd plan är den klassiska falska grönen: allt som står är
sant, och det som avgör saknas.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .handelser import (ARBETAR, Forloppsfel, PAGAR_MARKOR, STILLA,
                        UTANFOR_RACKVIDD)
from .yta import (Forlopp, RUBRIK_VET_INTE, _saknade_i_domarna, okorda_steg,
                  rendera)

_RAKNING = re.compile(r"HÄNDELSER: (\d+) totalt, visar (\d+)")
_DOLDA = re.compile(r"\.\.\. (\d+) till, ej visade\.")

REGLER = ("Y1", "Y2", "Y3", "Y4", "Y5", "Y6", "Y7", "Y8", "Y9", "Y10",
          "Y11")


@dataclass(frozen=True)
class Brott:
    regel: str
    vad: str

    def rad(self) -> str:
        return "%-4s %s" % (self.regel, self.vad)


@dataclass
class Forloppsdom:
    brott: List[Brott] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.brott

    @property
    def brutna(self) -> Tuple[str, ...]:
        ut: List[str] = []
        for b in self.brott:
            if b.regel not in ut:
                ut.append(b.regel)
        return tuple(ut)

    def text(self) -> str:
        if self.ok:
            return "FÖRLOPPSYTAN GODKÄND: %d regler prövade" % len(REGLER)
        rader = ["FÖRLOPPSYTAN FÄLLD: %d brott mot %d regler"
                 % (len(self.brott), len(self.brutna))]
        rader.extend("  " + b.rad() for b in self.brott)
        return "\n".join(rader)


def _utan_frammande_ord(f: Forlopp, text: str) -> str:
    """Texten med varje ordagrant block borttaget.

    En grinds egna ord är inte visningens påstående. Letar man efter
    visningens ord måste man först ta bort någon annans, annars kan en
    kompilatorrad fälla en visning som inte sagt något.
    """
    ut = text
    for ord_ in f.ordagranna():
        ut = ut.replace(ord_, "")
    return ut


def granska(f: Forlopp, text: Optional[str] = None) -> Forloppsdom:
    """Dömer texten mot protokollet. `text=None` renderar med standardytan."""
    if text is None:
        text = rendera(f)
    if not isinstance(text, str):
        raise Forloppsfel("en förloppsyta är text; renderaren lämnade %s"
                          % type(text).__name__)
    lage = f.lage
    brott: List[Brott] = []
    rader = text.splitlines()
    egna = _utan_frammande_ord(f, text)

    # Y1 -- läget står först, ordagrant
    forsta = next((r for r in rader if r.strip()), "")
    if forsta.strip() != "LÄGE: %s" % lage:
        brott.append(Brott("Y1", "första raden är %r, förloppet är %r"
                           % (forsta.strip(), "LÄGE: %s" % lage)))

    # Y2 -- ett stilla läge visar ingen pågåendemarkör
    if lage in STILLA and PAGAR_MARKOR in egna:
        brott.append(Brott(
            "Y2", "läget är %s men visningen skriver %r; ett fällt läge får "
                  "aldrig se ut som ett arbetande" % (lage, PAGAR_MARKOR)))

    # Y3 -- fallets skäl står ordagrant
    skal = f.fallskal()
    if skal is not None and skal not in text:
        brott.append(Brott("Y3", "fallets skäl saknas i texten: %r"
                           % (skal[:80],)))

    # Y4 -- varje främmande sträng, tecken för tecken
    for ord_ in f.ordagranna():
        if ord_ not in text:
            brott.append(Brott(
                "Y4", "någon annans ord nådde inte användaren ordagrant: %r. "
                      "En omskrivning på vägen ut mäter till slut sig själv "
                      "(50_grindar.md)" % (ord_[:80],)))

    # Y5 -- avsnittet om vad systemet inte vet
    if RUBRIK_VET_INTE not in text:
        brott.append(Brott("Y5", "visningen saknar avsnittet %r"
                           % RUBRIK_VET_INTE))
    else:
        saknade = [namn for namn, _skal in _rackvidden(f) if namn not in text]
        if saknade:
            brott.append(Brott(
                "Y5", "räckviddens poster saknas i visningen: %s. Ögat är "
                      "felfinnande, aldrig bevis (50_grindar.md)"
                      % ", ".join(saknade)))

    # Y6 -- en dom utan obligatorisk sektion visas inte som en dom
    for _namn, rad in _saknade_i_domarna(f):
        if rad not in text:
            brott.append(Brott(
                "Y6", "%s — visningen säger det inte. En rapport utan den "
                      "sektionen har ingen sådan grind alls, och den såg ut "
                      "som guld" % rad))

    # Y7 -- guld aldrig utan ögondom
    guld = f.guldbeslut()
    if guld is not None and not f.domar():
        if "UTAN ÖGONDOM" not in text:
            brott.append(Brott(
                "Y7", "ett guldbeslut visas utan ögondom under sig (regel "
                      "A-6, 26_appen.md)"))

    # Y8 -- trimningen säger hur mycket den dolde
    m = _RAKNING.search(text)
    if m is None:
        brott.append(Brott("Y8", "visningen säger inte hur många händelser "
                                 "den inte visade (M-60:s form)"))
    else:
        totalt, visade = int(m.group(1)), int(m.group(2))
        if totalt != len(f.handelser):
            brott.append(Brott("Y8", "visningen säger %d händelser, "
                                     "protokollet bär %d"
                               % (totalt, len(f.handelser))))
        dolda = totalt - visade
        d = _DOLDA.search(text)
        if dolda and (d is None or int(d.group(1)) != dolda):
            brott.append(Brott("Y8", "%d händelser doldes utan att visningen "
                                     "sa det" % dolda))

    # Y9 -- ett hjärtslag är inte framsteg
    #
    # Grinden räknar om det HÄR, med sin egen definition, i stället för att
    # fråga protokollet. Skälet är att det är just definitionen som kan vara
    # fel: ett förlopp som räknar hjärtslag som framsteg svarar glatt att
    # allt är i sin ordning. En grind som frågar den den dömer mäter till
    # slut sig själv.
    verkliga = [h for h in f.handelser if h.sort != "HJARTSLAG"]
    sista_verklig = verkliga[-1] if verkliga else None
    stillestand = f.klocka() - (sista_verklig.t if sista_verklig else f.t0)
    if lage == ARBETAR and stillestand > f.tystnadstak:
        brott.append(Brott(
            "Y9", "läget är ARBETAR men inget annat än hjärtslag har hänt på "
                  "%.1f s; ett hjärtslag som räknas som framsteg gör en död "
                  "körning odödlig" % stillestand))

    # Y10 -- ett arbetande läge namnger vad som pågår, och hur länge
    if lage == ARBETAR:
        sista = sista_verklig
        if sista is None:
            brott.append(Brott("Y10", "läget är ARBETAR utan en enda "
                                      "verklig händelse"))
        else:
            if sista.sort not in egna:
                brott.append(Brott(
                    "Y10", "läget är ARBETAR men visningen namnger inte vad "
                           "som pågår (%s)" % sista.sort))
            if " s sedan" not in egna:
                brott.append(Brott(
                    "Y10", "läget är ARBETAR men visningen säger inte hur "
                           "länge sedan något hände"))
    # Y11 -- en avslutad körning räknar stegen som aldrig kördes
    for steg in okorda_steg(f, lage):
        if ("steg " + steg.namn) not in text:
            brott.append(Brott(
                "Y11", "steget %s kördes aldrig, och visningen säger det "
                       "inte. Ett svar över en halvkörd plan är sant i varje "
                       "rad och falskt som helhet" % steg.namn))
    return Forloppsdom(brott)


def _rackvidden(f: Forlopp):
    return [(o.namn, o.skal) for o in f.ovissheter
            if o.klass == UTANFOR_RACKVIDD]


def granska_eller_kasta(f: Forlopp, text: Optional[str] = None) -> str:
    """Som `granska`, men kastar. Använd i en väg som INTE får leverera."""
    if text is None:
        text = rendera(f)
    dom = granska(f, text)
    if not dom.ok:
        raise Forloppsfel(dom.text())
    return text

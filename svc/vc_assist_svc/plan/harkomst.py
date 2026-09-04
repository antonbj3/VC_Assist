# -*- coding: utf-8 -*-
"""Harkomst: varje krav i en spec ska kunna peka pa var det kom ifran.

DET KRAV SOM GOR MODULEN NODVANDIG

    Detaljeringen fran grundbegaran far inte hitta pa krav operatoren aldrig
    stallde. Ett antaget krav ska vara MARKT som antaget och ga att se.

spec.py har redan Antagande med motiv, och forfining.py har redan regeln att
allt som inte star i begaran gar genom anta() eller fraga(). Det som SAKNADES
var kopplingen at andra hallet: ett villkor i specen bar inget falt som sager
vilken av de tva vagarna det kom in genom. Ett uppfunnet krav sag darfor
likadant ut som ett krav operatoren faktiskt stallde.

Harkomst ar det faltet, och det ar mekaniskt provbart:

    begaran    belagget ska sta ORDAGRANT i operatorens text. Kontrollen ar en
               delstrangsmatchning pa normaliserad text - inte en asikt.
    antagande  belagget ska namna ett antagande som FINNS i specen, och det
               antagandet bar redan sitt motiv.
    fraga      belagget ska namna en fraga som finns i specen. Kravet ar da
               inte fastslaget an, och planen ar hogst en kandidat.
    katalog    belagget ar "<nyckel>#<falt>" - vilken post och vilket falt.
    datablad   samma form. Ett datablad ar mattt i VC, en katalogpost ar last.
    bank       belagget ar "<uppgift>#<falt>" ur bank/uppgifter.
    layout     belagget namner den placering eller relation som gav talet.

INGET "standard" I LISTAN, OCH DET AR AVSIKTEN. Vill planeringen valja ett
varde at operatoren far den skriva ett Antagande med motiv och peka pa det.
Det finns ingen kalla som betyder "vi tyckte sa".

HK2 AR MODULENS SKARPASTE KONTROLL. Ett krav som pastar sig komma ur begaran,
men vars ord inte star dar, ar precis det uppfunna kravet - och det ar den
enda av felklasserna som fangar en modell som SKRIVER om operatorens ord i
stallet for att citera dem.

Endast standardbiblioteket.
"""
from __future__ import annotations

import re

from .fel import Specfel

# Sluten lista. En kalla som inte star har finns inte, och ett krav med en
# okand kalla avvisas vid konstruktionen.
KALLOR = ("begaran", "antagande", "fraga", "katalog", "datablad", "bank",
          "layout")

# Kallor vars belagg ska peka ut BADE posten och faltet, med '#' emellan.
# Utan faltet gar talet inte att sla upp igen, och en harkomst man inte kan
# folja ar en formulering och inte en harkomst.
KALLOR_MED_FALT = ("katalog", "datablad", "bank")

# Kortaste belagg som sager nagot alls. Ett belagg pa ett eller tva tecken
# matchar nastan vilken text som helst och skulle gora HK2 trivialt sann -
# samma falla som en facitmall utan tal (bank/schema.py).
MIN_BELAGG_TECKEN = 3           # Satt av M-63.

LINTKODER = {
    "HK1_UTAN_HARKOMST": "kravet bar ingen harkomst",
    "HK2_FALSK_BEGARAN": "kravet sager sig komma ur begaran, men orden star "
                         "inte dar",
    "HK3_OKANT_ANTAGANDE": "kravet pekar pa ett antagande som inte finns i "
                           "specen",
    "HK4_OKAND_FRAGA": "kravet pekar pa en fraga som inte finns i specen",
}


def normalisera(text):
    """Gemener, a/o for a-ring och prickar, och ett mellanslag mellan orden.

    Banken skriver 'transportor' och operatoren 'transportör'; en radbrytning
    mitt i en mening ska inte gora ett belagg falskt. Normaliseringen ar
    avsiktligt grov och gemensam for hela lagret - forfining.py anvander samma
    funktion for att hitta ord i katalogen.
    """
    text = (text or "").lower()
    for fran, till in (("å", "a"), ("ä", "a"), ("ö", "o"), ("é", "e")):
        text = text.replace(fran, till)
    return re.sub(r"\s+", " ", text).strip()


class Harkomst(object):
    """Var ett krav kom ifran, i en form som gar att sla upp."""

    __slots__ = ("kalla", "belagg")

    def __init__(self, kalla, belagg):
        self.kalla = kalla
        self.belagg = belagg
        problem = []
        if kalla not in KALLOR:
            problem.append("okand kalla %r; kanda ar %s"
                           % (kalla, ", ".join(KALLOR)))
        if not isinstance(belagg, str) or len(belagg.strip()) < MIN_BELAGG_TECKEN:
            problem.append("belagget maste vara text pa minst %d tecken, fick %r"
                           % (MIN_BELAGG_TECKEN, belagg))
        elif kalla in KALLOR_MED_FALT and "#" not in belagg:
            problem.append(
                "en harkomst ur %s ska peka ut bade posten och faltet som "
                "'<nyckel>#<falt>'; %r gar inte att sla upp igen"
                % (kalla, belagg))
        if problem:
            raise Specfel("harkomsten %r" % (kalla,), problem)

    def __repr__(self):
        return "Harkomst(%s: %s)" % (self.kalla, self.belagg)

    def __eq__(self, annan):
        return (isinstance(annan, Harkomst) and annan.kalla == self.kalla
                and annan.belagg == self.belagg)

    def __hash__(self):
        return hash((self.kalla, self.belagg))

    def text(self):
        """Raden operatoren far se bredvid kravet."""
        if self.kalla == "begaran":
            return 'ur din begaran: "%s"' % self.belagg
        if self.kalla == "antagande":
            return "antaget av oss: %s" % self.belagg
        if self.kalla == "fraga":
            return "vantar pa ditt svar: %s" % self.belagg
        return "ur %s: %s" % (self.kalla, self.belagg)

    def granska(self, vad, begaran_text, antaganden=(), fragor=()):
        """[(lintkod, text)]. Tom lista = harkomsten gar att folja.

        Kastar aldrig. En granskning som kraschar pa ett trasigt krav sager
        ingenting om vad som var trasigt (S10 i 96_ingen_skuld.md).
        """
        if self.kalla == "begaran":
            if normalisera(self.belagg) not in normalisera(begaran_text):
                return [("HK2_FALSK_BEGARAN",
                         "%s sager sig komma ur begaran med orden %r, men de "
                         "orden star inte i begaran. Ett krav vi hittat pa ska "
                         "vara ett markt antagande, inte operatorens ord"
                         % (vad, self.belagg))]
            return []
        if self.kalla == "antagande":
            if self.belagg not in set(antaganden):
                return [("HK3_OKANT_ANTAGANDE",
                         "%s pekar pa antagandet %r, som inte finns i specen; "
                         "specen bar %s"
                         % (vad, self.belagg,
                            ", ".join(sorted(antaganden)) or "inga antaganden"))]
            return []
        if self.kalla == "fraga":
            if self.belagg not in set(fragor):
                return [("HK4_OKAND_FRAGA",
                         "%s pekar pa fragan %r, som inte finns i specen; "
                         "specen bar %s"
                         % (vad, self.belagg,
                            ", ".join(sorted(fragor)) or "inga fragor"))]
            return []
        return []

    def till_json(self):
        return {"kalla": self.kalla, "belagg": self.belagg}

    @classmethod
    def fran_json(cls, data):
        if not isinstance(data, dict) or set(data) != {"kalla", "belagg"}:
            raise Specfel("harkomst",
                          ["forvantade precis nycklarna belagg och kalla, fick %s"
                           % (", ".join(sorted(data))
                              if isinstance(data, dict) else type(data).__name__)])
        return cls(data["kalla"], data["belagg"])


def ur_begaran(belagg):
    """Kortform for det vanligaste fallet: operatorens egna ord."""
    return Harkomst("begaran", belagg)


def granska_alla(poster, begaran_text, antaganden=(), fragor=()):
    """[(lintkod, text)] over manga krav.

    `poster` ar (vad, harkomst)-par. En post utan harkomst ar HK1: kravet
    finns, men ingen kan saga varifran det kom.
    """
    ut = []
    namn = [a.vad for a in antaganden]
    ids = [f.id for f in fragor]
    for vad, harkomst in poster:
        if harkomst is None:
            ut.append(("HK1_UTAN_HARKOMST",
                       "%s bar ingen harkomst; ett krav ingen kan spara till "
                       "begaran, ett antagande eller en katalogpost ar ett "
                       "krav vi hittat pa" % (vad,)))
            continue
        ut += harkomst.granska(vad, begaran_text, namn, ids)
    return ut
